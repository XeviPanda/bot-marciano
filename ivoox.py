"""
ivoox.py — De dónde sacamos los episodios.

Lee **dos sitios distintos** y usa el que funcione, por este orden:

  1. El RSS del podcast (feeds.ivoox.com). Es un solo archivo con todo:
     título, enlace, portada, duración, descripción y fecha. Una petición
     por podcast y listo.

  2. Si el RSS falla, la página web del podcast (www.ivoox.com), que es lo
     que hacíamos antes: la lista de episodios, y luego la ficha de cada uno.

Esto no es paranoia, es historia:

  · Mayo 2026 — los RSS de El Aftershow y Marcianos se congelaron: servían
    siempre los mismos 100 episodios aunque la web estuviera al día. Por eso
    el bot nació leyendo la web.
  · Noviembre 2026 — iVoox empezó a devolver "502 Bad Gateway" a las
    peticiones que vienen de los servidores de GitHub, y el bot se calló tres
    días. Desde casa la web se veía perfectamente; desde GitHub, no.
  · Y a la vez, iVoox arregló los RSS: ahora traen el catálogo completo.

Moraleja: cualquiera de los dos puede romperse, pero es muy raro que se
rompan los dos a la vez. Así que probamos los dos.
"""

import email.utils
import html as htmlmod
import json
import re
import xml.etree.ElementTree as ET

import requests

# Algunas webs rechazan las peticiones que no parecen un navegador de verdad.
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}

TIEMPO_MAXIMO = 30  # segundos que esperamos a que iVoox conteste

# Cuántas letras de la descripción metemos en el mensaje. Telegram no deja pasar
# de 1024 caracteres en el pie de una foto, y con esto vamos sobrados.
LARGO_DESCRIPCION = 350

# Los RSS de iVoox traen el podcast entero (más de mil episodios en algunos).
# No necesitamos tantos: con los últimos vamos de sobra y el programa va ligero.
EPISODIOS_QUE_MIRAMOS = 25


def _descargar(url):
    respuesta = requests.get(url, headers=CABECERAS, timeout=TIEMPO_MAXIMO)
    respuesta.raise_for_status()
    return respuesta.text


# El número que identifica a un episodio sale de su dirección:
#   https://www.ivoox.com/lo-que-sea-audios-mp3_rf_182949557_1.html
# Ese número SIEMPRE va a más, y es lo único que usamos para saber qué es nuevo.
NUMERO_DE_EPISODIO = re.compile(r"_rf_(\d+)_1\.html")


# ---------------------------------------------------------------------------
# Camino 1: el RSS
# ---------------------------------------------------------------------------

FEED = "https://feeds.ivoox.com/feed_fg_f{id_ivoox}_filtro_1.xml"
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def desde_el_rss(id_ivoox):
    """
    Devuelve los episodios del RSS, del más nuevo al más viejo, ya completos:

        [{"id": 182949557, "url": "...", "ficha": {...}}, ...]

    Como el RSS ya trae todos los datos, no hace falta pedir nada más.
    """
    arbol = ET.fromstring(_descargar(FEED.format(id_ivoox=id_ivoox)))

    episodios = []
    for item in arbol.iter("item"):
        enlace = (item.findtext("link") or "").strip()
        numero = NUMERO_DE_EPISODIO.search(enlace)
        if not numero:
            continue

        imagen = item.find(ITUNES + "image")

        episodios.append({
            "id": int(numero.group(1)),
            "url": enlace,
            "fecha": _fecha(item.findtext("pubDate")),
            "ficha": {
                "titulo": limpiar(item.findtext("title") or ""),
                "descripcion": recortar(limpiar(item.findtext("description") or ""),
                                        LARGO_DESCRIPCION),
                "portada": (imagen.get("href") if imagen is not None else "") or "",
                "duracion": duracion_en_bonito(item.findtext(ITUNES + "duration") or ""),
                "podcast": "",   # lo pone main.py, con el nombre de podcasts.py
                "url": enlace,
            },
        })

        if len(episodios) >= EPISODIOS_QUE_MIRAMOS:
            break

    return episodios


def _fecha(pubdate):
    """Convierte 'Thu, 05 Nov 2026 00:05:00 +0200' en una fecha de verdad."""
    if not pubdate:
        return None
    try:
        return email.utils.parsedate_to_datetime(pubdate.strip())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Camino 2: la página web (plan B)
# ---------------------------------------------------------------------------

# El nombre que va antes de "_sq_f" en la dirección da igual: iVoox solo mira el
# número. Por eso podemos escribir "podcast-x" y nos vale para todos.
PAGINA_PODCAST = "https://www.ivoox.com/podcast-x_sq_f{id_ivoox}_1.html"

ENLACE_EPISODIO = re.compile(r'href="(/[^"]*_rf_(\d+)_1\.html)"')


def desde_la_web(id_ivoox):
    """
    Devuelve los episodios que se ven en la portada del podcast, del más nuevo
    al más viejo. Aquí la ficha va vacía: se pide luego, y solo la de los
    episodios que resulten ser nuevos.
    """
    pagina = _descargar(PAGINA_PODCAST.format(id_ivoox=id_ivoox))

    episodios = []
    ya_vistos = set()

    for camino, numero in ENLACE_EPISODIO.findall(pagina):
        numero = int(numero)
        if numero in ya_vistos:
            continue
        ya_vistos.add(numero)
        episodios.append({
            "id": numero,
            "url": "https://www.ivoox.com" + camino,
            "fecha": None,   # la web no la da; no pasa nada, ver main.py
            "ficha": None,
        })

    return episodios


# ---------------------------------------------------------------------------
# El de verdad: prueba uno y si no, el otro
# ---------------------------------------------------------------------------

def episodios_visibles(id_ivoox):
    """Intenta el RSS; si falla o viene vacío, tira de la web."""
    try:
        episodios = desde_el_rss(id_ivoox)
        if episodios:
            return episodios
        print("   ⚠️  el RSS no traía episodios; pruebo con la web.")
    except Exception as error:
        print(f"   ⚠️  el RSS ha fallado ({type(error).__name__}: {error}). "
              f"Pruebo con la web.")

    return desde_la_web(id_ivoox)


# ---------------------------------------------------------------------------
# La ficha de un episodio, para cuando venimos por la web
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
    Lee la página de un episodio y devuelve sus datos.
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
        "podcast": "",
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


# iVoox escribe la duración de dos maneras según de dónde la saquemos:
#   · en el RSS, como un reloj:   "02:02:24"  o  "37:25"  o  "125" (segundos)
#   · en la web, en el formato raro de siempre:  "PT2H2M24S"
DURACION_RARA = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def duracion_en_bonito(texto):
    """Convierte cualquiera de los dos formatos en '2 h 2 min'. Si no, devuelve ''."""
    if not texto:
        return ""

    texto = texto.strip()
    horas = minutos = 0

    if texto.upper().startswith("PT"):
        encaje = DURACION_RARA.fullmatch(texto)
        if not encaje:
            return ""
        horas, minutos, _segundos = (int(x) if x else 0 for x in encaje.groups())

    elif ":" in texto:
        trozos = texto.split(":")
        if not all(t.strip().isdigit() for t in trozos) or len(trozos) > 3:
            return ""
        trozos = [int(t) for t in trozos]
        if len(trozos) == 3:
            horas, minutos, _ = trozos
        else:
            minutos, _ = trozos

    elif texto.isdigit():
        total = int(texto) // 60
        horas, minutos = divmod(total, 60)

    else:
        return ""

    if horas and minutos:
        return f"{horas} h {minutos} min"
    if horas:
        return f"{horas} h"
    if minutos:
        return f"{minutos} min"
    return ""
