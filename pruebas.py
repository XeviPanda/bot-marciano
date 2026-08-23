"""
pruebas.py — Comprueba que el bot hace lo que creemos que hace.

Ejecútalo con:   python pruebas.py

No toca internet ni manda nada a Telegram: usa páginas de mentira escritas aquí
mismo. Si sale todo en verde, se puede subir con tranquilidad.
"""

import json
import sys

import ivoox
import main
import telegram


fallos = []


def comprobar(nombre, condicion, detalle=""):
    if condicion:
        print(f"✅ {nombre}")
    else:
        print(f"❌ {nombre}   {detalle}")
        fallos.append(nombre)


# ---------------------------------------------------------------------------
# Páginas de mentira
# ---------------------------------------------------------------------------

PAGINA_DE_PODCAST = """
<html><body>
  <a href="/en/uno-audios-mp3_rf_300_1.html">Episodio nuevo</a>
  <a href="/en/uno-audios-mp3_rf_300_1.html">El mismo, repetido en la portada</a>
  <a href="/en/dos-audios-mp3_rf_299_1.html">Episodio anterior</a>
  <a href="/en/tres-audios-mp3_rf_298_1.html">Otro más viejo</a>
  <a href="/en/podcast-otra-cosa_sq_f999_1.html">Esto no es un episodio</a>
</body></html>
"""


def pagina_de_episodio(nombre, id_serie="1315616", duracion="PT1H5M8S"):
    ficha = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": []},
            {
                "@type": "PodcastEpisode",
                "name": nombre,
                "description": "Una descripción normal y corriente.\r\n\r\n"
                               "⠀⠀⠀⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⠀⠀⠀\r\n"
                               "Y una segunda línea con texto de verdad.",
                "image": "https://static-1.ivoox.com/audios/x/portada_XXL.jpg",
                "duration": duracion,
                "author": {"@type": "Person", "name": "El Aftershow"},
                "partOfSeries": {
                    "@id": f"https://www.ivoox.com/podcast-x_sq_f{id_serie}_1.html#podcast"
                },
                "url": "https://www.ivoox.com/en/uno-audios-mp3_rf_300_1.html",
            },
        ],
    }
    return ('<html><head><script type="application/ld+json">'
            + json.dumps(ficha, ensure_ascii=False)
            + "</script></head><body>hola</body></html>")


# ---------------------------------------------------------------------------
# 1. Leer la lista de episodios
# ---------------------------------------------------------------------------

def prueba_lista_de_episodios():
    ivoox._descargar = lambda url: PAGINA_DE_PODCAST
    episodios = ivoox.episodios_visibles("1315616")

    comprobar("La lista sale del más nuevo al más viejo",
              [e["id"] for e in episodios] == [300, 299, 298],
              f"salió {[e['id'] for e in episodios]}")

    comprobar("No cuela el mismo episodio dos veces",
              len(episodios) == 3)

    comprobar("La dirección del episodio se monta entera",
              episodios[0]["url"] ==
              "https://www.ivoox.com/en/uno-audios-mp3_rf_300_1.html")


# ---------------------------------------------------------------------------
# 2. Leer la ficha de un episodio
# ---------------------------------------------------------------------------

def prueba_ficha():
    ivoox._descargar = lambda url: pagina_de_episodio("MAR 529. Un título")
    ficha = ivoox.detalle("https://ejemplo", "1315616")

    comprobar("Saca el título", ficha["titulo"] == "MAR 529. Un título")
    comprobar("Saca el podcast", ficha["podcast"] == "El Aftershow")
    comprobar("Saca la portada", ficha["portada"].endswith("portada_XXL.jpg"))
    comprobar("Traduce la duración", ficha["duracion"] == "1 h 5 min",
              f"salió {ficha['duracion']!r}")

    comprobar("Tira los dibujos de puntitos de la descripción",
              "⣿" not in ficha["descripcion"],
              f"salió {ficha['descripcion']!r}")
    comprobar("Pero conserva el texto de verdad",
              "segunda línea" in ficha["descripcion"])


def prueba_ficha_de_otro_podcast():
    """El recomendado de otro podcast que iVoox mete en la misma página."""
    ivoox._descargar = lambda url: pagina_de_episodio("De otro sitio", id_serie="999999")
    ficha = ivoox.detalle("https://ejemplo", "1315616")

    comprobar("Descarta el episodio que no es de este podcast", ficha is None)


def prueba_pagina_rota():
    ivoox._descargar = lambda url: "<html><body>iVoox ha cambiado la web</body></html>"

    comprobar("Si no encuentra la ficha, devuelve None en vez de reventar",
              ivoox.detalle("https://ejemplo", "1315616") is None)
    comprobar("Si no encuentra episodios, devuelve lista vacía",
              ivoox.episodios_visibles("1315616") == [])


# ---------------------------------------------------------------------------
# 3. Duraciones y recortes
# ---------------------------------------------------------------------------

def prueba_duraciones():
    casos = {
        "PT1H5M8S": "1 h 5 min",
        "PT2H34M54S": "2 h 34 min",
        "PT42M35S": "42 min",
        "PT3H": "3 h",
        "": "",
        "cualquier cosa": "",
    }
    for entrada, esperado in casos.items():
        comprobar(f"Duración {entrada!r} → {esperado!r}",
                  ivoox.duracion_en_bonito(entrada) == esperado,
                  f"salió {ivoox.duracion_en_bonito(entrada)!r}")


def prueba_recorte():
    largo = "palabra " * 100
    corto = ivoox.recortar(largo, 50)

    comprobar("Recorta a la medida", len(corto) <= 51, f"salió {len(corto)}")
    comprobar("Y avisa de que ha recortado", corto.endswith("…"))
    comprobar("No toca lo que ya es corto", ivoox.recortar("hola", 50) == "hola")


# ---------------------------------------------------------------------------
# 4. El mensaje que llega a Telegram
# ---------------------------------------------------------------------------

EPISODIO = {
    "podcast": "El Aftershow",
    "titulo": "LINTERNAS 01 <con un signo raro>",
    "descripcion": "Dos tíos hablando de Lanterns.",
    "duracion": "1 h 5 min",
    "portada": "https://static-1.ivoox.com/portada.jpg",
    "url": "https://www.ivoox.com/episodio.html",
    "spotify": "https://open.spotify.com/show/xxx",
}


def prueba_mensaje():
    texto = telegram.formatear(EPISODIO)

    comprobar("El nombre del podcast va arriba", texto.startswith("🎙️ <b>El Aftershow</b>"))
    comprobar("Los signos raros del título no rompen el mensaje",
              "&lt;con un signo raro&gt;" in texto)
    comprobar("Sale la duración", "1 h 5 min" in texto)

    gigante = dict(EPISODIO, descripcion="x" * 5000)
    comprobar("Nunca pasa del límite de Telegram",
              len(telegram.formatear(gigante)) <= telegram.LIMITE_PIE_DE_FOTO,
              f"salió {len(telegram.formatear(gigante))}")


def prueba_botones():
    con = telegram.botones(EPISODIO)
    comprobar("Con Spotify salen dos botones",
              len(con["inline_keyboard"][0]) == 2)

    sin = telegram.botones(dict(EPISODIO, spotify=""))
    comprobar("Sin Spotify sale solo el de iVoox",
              len(sin["inline_keyboard"][0]) == 1)


# ---------------------------------------------------------------------------
# 5. La memoria: qué avisa y qué no
# ---------------------------------------------------------------------------

def _falsos_episodios(ids):
    return [{"id": i, "url": f"https://ejemplo/{i}"} for i in ids]


def prueba_estreno_silencioso():
    ivoox.episodios_visibles = lambda id_ivoox: _falsos_episodios([300, 299, 298])
    estado = {"ultimos": {}}

    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "1315616"}, estado)

    comprobar("La primera vez no avisa de nada", nuevos == [] and es_estreno)
    comprobar("Pero apunta por dónde va", estado["ultimos"]["1315616"] == 300)


def prueba_modo_estreno():
    """El día que abres canal: en vez de callarse, publica el último de cada uno."""
    ivoox.episodios_visibles = lambda id_ivoox: _falsos_episodios([300, 299, 298])
    estado = {"ultimos": {}}

    nuevos, es_estreno = main.episodios_nuevos_de(
        {"id_ivoox": "1315616"}, estado, estrenar=True)

    comprobar("En modo estreno publica el último episodio",
              [e["id"] for e in nuevos] == [300],
              f"salió {[e['id'] for e in nuevos]}")
    comprobar("Y no lo trata como estreno silencioso", es_estreno is False)
    comprobar("Deja el marcador justo antes, para que el último cuente como nuevo",
              estado["ultimos"]["1315616"] == 299)


def prueba_modo_estreno_no_repite():
    """Si el podcast ya se conocía, el modo estreno no toca nada."""
    ivoox.episodios_visibles = lambda id_ivoox: _falsos_episodios([300, 299])
    estado = {"ultimos": {"1315616": 300}}

    nuevos, _ = main.episodios_nuevos_de(
        {"id_ivoox": "1315616"}, estado, estrenar=True)

    comprobar("El modo estreno no reenvía lo ya avisado", nuevos == [])


def prueba_episodio_nuevo():
    ivoox.episodios_visibles = lambda id_ivoox: _falsos_episodios([302, 301, 300, 299])
    estado = {"ultimos": {"1315616": 300}}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "1315616"}, estado)

    comprobar("Avisa solo de lo que no había visto",
              [e["id"] for e in nuevos] == [301, 302],
              f"salió {[e['id'] for e in nuevos]}")
    comprobar("Y en orden: primero el más viejo", nuevos[0]["id"] == 301)


def prueba_nada_nuevo():
    ivoox.episodios_visibles = lambda id_ivoox: _falsos_episodios([300, 299])
    estado = {"ultimos": {"1315616": 300}}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "1315616"}, estado)
    comprobar("Si no hay nada nuevo, no avisa", nuevos == [])


def prueba_guardian_de_avalanchas():
    ivoox.episodios_visibles = lambda id_ivoox: _falsos_episodios(
        [310, 309, 308, 307, 306, 305, 304, 303, 302, 301]
    )
    estado = {"ultimos": {"1315616": 300}}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "1315616"}, estado)

    comprobar("Con diez de golpe, avisa solo del último",
              [e["id"] for e in nuevos] == [310],
              f"salió {[e['id'] for e in nuevos]}")
    comprobar("Y da los otros nueve por vistos",
              estado["ultimos"]["1315616"] == 309)


def prueba_la_memoria_no_crece():
    estado = {"ultimos": {str(i): i for i in range(5)}}
    guardado = json.dumps({"ultimos": estado["ultimos"]})

    comprobar("El estado es minúsculo pase lo que pase", len(guardado) < 200)


# ---------------------------------------------------------------------------

def todas():
    prueba_lista_de_episodios()
    prueba_ficha()
    prueba_ficha_de_otro_podcast()
    prueba_pagina_rota()
    prueba_duraciones()
    prueba_recorte()
    prueba_mensaje()
    prueba_botones()
    prueba_estreno_silencioso()
    prueba_modo_estreno()
    prueba_modo_estreno_no_repite()
    prueba_episodio_nuevo()
    prueba_nada_nuevo()
    prueba_guardian_de_avalanchas()
    prueba_la_memoria_no_crece()


if __name__ == "__main__":
    todas()
    print()
    if fallos:
        print(f"❌ {len(fallos)} prueba(s) mal: {', '.join(fallos)}")
        sys.exit(1)
    print("🎉 Todo bien. Se puede subir.")
