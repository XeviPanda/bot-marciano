"""
ivoox.py — De dónde sacamos los episodios.

IMPORTANTE: esto NO usa el RSS de iVoox.

El 23 de agosto de 2026 comprobamos que los feeds RSS de El Aftershow y de
Marcianos en un Tren llevaban meses congelados (servían siempre los mismos 100
episodios) aunque en la web seguían saliendo programas nuevos. Es un fallo de
iVoox. Así que este bot lee directamente la página web, que sí está al día.

Cómo funciona, en dos pasos:

  1. Pide la página del podcast. En el HTML, cada episodio es un enlace que
     acaba en "_rf_<numero>_1.html". Ese <numero> es el identificador del
     episodio y SIEMPRE va a más: el episodio más nuevo tiene el número más
     alto. Salen ordenados, el más nuevo primero.

  2. Para cada episodio que nos interese, pide su página y lee la ficha que
     iVoox deja escondida dentro (un bloque "application/ld+json"). Ahí están
     el título, la portada, la descripción y la duración, limpios.
"""

import html as htmlmod
import json
import re

import requests

# Algunas webs rechazan las peticiones que no parecen un navegador de verdad.
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

TIEMPO_MAXIMO = 30  # segundos que esperamos a que iVoox conteste

# Cuántas letras de la descripción metemos en el mensaje. Telegram no deja pasar
# de 1024 caracteres en el pie de una foto, y con esto vamos sobrados.
LARGO_DESCRIPCION = 350


def _descargar(url):
    respuesta = requests.get(url, headers=CABECERAS, timeout=TIEMPO_MAXIMO)
    respuesta.raise_for_status()
    return respuesta.text


# ---------------------------------------------------------------------------
# Paso 1: qué episodios hay ahora mismo en un podcast
# ---------------------------------------------------------------------------

# El nombre que va antes de "_sq_f" en la dirección da igual: iVoox solo mira el
# número. Por eso podemos escribir "podcast-x" y nos vale para todos.
PAGINA_PODCAST = "https://www.ivoox.com/podcast-x_sq_f{id_ivoox}_1.html"

ENLACE_EPISODIO = re.compile(r'href="(/[^"]*_rf_(\d+)_1\.html)"')


def episodios_visibles(id_ivoox):
    """
    Devuelve la lista de episodios que se ven en la portada del podcast,
    del más nuevo al más viejo:

        [{"id": 179260903, "url": "https://www.ivoox.com/..."}, ...]
    """
    pagina = _descargar(PAGINA_PODCAST.format(id_ivoox=id_ivoox))

    episodios = []
    ya_vistos = set()

    for camino, numero in ENLACE_EPISODIO.findall(pagina):
        numero = int(numero)
        if numero in ya_vistos:
            continue
        ya_vistos.add(numero)
        episodios.append({"id": numero, "url": "https://www.ivoox.com" + camino})

    return episodios


# ---------------------------------------------------------------------------
# Paso 2: la ficha de un episodio concreto
# ---------------------------------------------------------------------------

FICHA_ESCONDIDA = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.DOTALL
)


def _buscar_ficha_de_episodio(pagina):
    """Rebusca en la página el bloque de datos del episodio. Devuelve None si no está."""
    for bloque in FICHA_ESCONDIDA.findall(pagina):
        try:
            datos = json.loads(bloque)
        except Exception:
            continue

        # A veces viene suelto y a veces dentro de una lista llamada "@graph".
        candidatos = datos.get("@graph", [datos]) if isinstance(datos, dict) else datos
        for candidato in candidatos:
            if isinstance(candidato, dict) and candidato.get("@type") == "PodcastEpisode":
                return candidato

    return None


def detalle(url_episodio, id_ivoox_esperado=None):
    """
    Lee la página de un episodio y devuelve sus datos:

        {"titulo", "descripcion", "portada", "duracion", "podcast", "url"}

    Si algo no cuadra devuelve None, y el que llame decide qué hacer.
    """
    pagina = _descargar(url_episodio)
    ficha = _buscar_ficha_de_episodio(pagina)

    if not ficha:
        return None

    # Comprobación de seguridad: que el episodio sea REALMENTE de este podcast y
    # no de la lista de recomendados que iVoox mete en la misma página.
    if id_ivoox_esperado:
        serie = str((ficha.get("partOfSeries") or {}).get("@id", ""))
        if f"_sq_f{id_ivoox_esperado}_" not in serie:
            return None

    return {
        "titulo": limpiar(ficha.get("name", "")),
        "descripcion": recortar(limpiar(ficha.get("description", "")), LARGO_DESCRIPCION),
        "portada": ficha.get("image", "") or "",
        "duracion": duracion_en_bonito(ficha.get("duration", "")),
        "podcast": ((ficha.get("author") or {}).get("name") or "").strip(),
        "url": ficha.get("url") or url_episodio,
    }


# ---------------------------------------------------------------------------
# Herramientas de limpieza
# ---------------------------------------------------------------------------

# Muchas descripciones de Red Marciana llevan dibujos hechos con caracteres raros
# (el Daredevil en "puntitos", por ejemplo). Eso en Telegram queda fatal, así que
# tiramos las líneas que casi no tienen letras ni números.
def _es_linea_de_dibujo(linea):
    if len(linea) < 8:
        return False
    letras = sum(1 for c in linea if c.isalnum())
    return letras / len(linea) < 0.35


def limpiar(texto):
    """Quita etiquetas HTML, dibujitos y espacios de más."""
    if not texto:
        return ""

    texto = re.sub(r"<br\s*/?>", "\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"</p>", "\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = htmlmod.unescape(texto)

    lineas = [l.strip() for l in texto.replace("\r", "\n").split("\n")]
    lineas = [l for l in lineas if l and not _es_linea_de_dibujo(l)]

    # Mantenemos los saltos de línea: así el mensaje se parece a lo que escribió
    # quien subió el episodio, en vez de quedar todo apelmazado en un párrafo.
    texto = "\n".join(lineas)
    return re.sub(r"[ \t]+", " ", texto).strip()


def recortar(texto, largo):
    """Corta un texto sin partir palabras por la mitad."""
    if len(texto) <= largo:
        return texto

    corte = texto[:largo]

    # Preferimos cortar en un punto y aparte; si no hay, en un espacio.
    salto = corte.rfind("\n")
    espacio = corte.rfind(" ")
    if salto > largo * 0.5:
        return corte[:salto].rstrip() + "…"
    if espacio > largo * 0.6:
        corte = corte[:espacio]

    return corte.rstrip(" \n.,;:-") + "…"


DURACION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def duracion_en_bonito(texto):
    """Convierte 'PT1H5M8S' en '1 h 5 min'. Si no lo entiende, devuelve ''."""
    if not texto:
        return ""

    encaje = DURACION.fullmatch(texto.strip())
    if not encaje:
        return ""

    horas, minutos, _segundos = (int(x) if x else 0 for x in encaje.groups())

    if horas and minutos:
        return f"{horas} h {minutos} min"
    if horas:
        return f"{horas} h"
    if minutos:
        return f"{minutos} min"
    return ""
