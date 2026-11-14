"""
pruebas.py — Comprueba que el bot hace lo que creemos que hace.

Ejecútalo con:   python pruebas.py

No toca internet ni manda nada a Telegram: usa páginas de mentira escritas aquí
mismo. Si sale todo en verde, se puede subir con tranquilidad.
"""

import contextlib
import email.utils
import io
import json
import sys
from datetime import datetime, timedelta, timezone

import apple
import ivoox
import main
import telegram


fallos = []

# Las pruebas sustituyen ivoox._descargar por páginas de mentira. Nos quedamos
# con la de verdad para poder probarla a ella también.
_DESCARGAR_DE_VERDAD = ivoox._descargar
_EPISODIOS_VISIBLES_DE_VERDAD = ivoox.episodios_visibles


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


RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0"><channel>
  <title>Marcianos en un Tren.</title>
  <item>
    <title><![CDATA[MAR 540. Chris Claremont y los X-Men]]></title>
    <link>https://www.ivoox.com/mar-540-audios-mp3_rf_300_1.html</link>
    <description><![CDATA[Prepárate: una descripción con acentos, eñes y símbolos.&#13;
&#13;
&#x2800;&#x2800;&#x28FF;&#x28FF;&#x28FF;&#x2800;&#x2800;&#x2800;&#x2800;&#x28FF;&#x28FF;&#x28FF;&#x2800;&#x2800;&#13;
Y una segunda linea con texto de verdad.]]></description>
    <pubDate>Thu, 05 Nov 2026 00:05:00 +0200</pubDate>
    <itunes:duration>02:02:24</itunes:duration>
    <guid>https://www.ivoox.com/300</guid>
    <itunes:image href="https://static-1.ivoox.com/audios/x/portada_XXL.jpg"/>
  </item>
  <item>
    <title>MAR 539</title>
    <link>https://www.ivoox.com/mar-539-audios-mp3_rf_299_1.html</link>
    <description>Otro</description>
    <itunes:duration>45:00</itunes:duration>
  </item>
  <item>
    <title>Un trailer sin numero de episodio</title>
    <link>https://www.ivoox.com/promo</link>
    <description>No deberia colarse</description>
  </item>
</channel></rss>"""


# ---------------------------------------------------------------------------
# 0. El RSS, que es por donde se entra ahora
# ---------------------------------------------------------------------------

def prueba_rss():
    ivoox._descargar = lambda url: RSS
    eps = ivoox.desde_el_rss("1311035")

    comprobar("Del RSS salen los episodios en orden",
              [e["id"] for e in eps] == [300, 299], f"salio {[e['id'] for e in eps]}")
    comprobar("Lo que no tiene numero de episodio no se cuela", len(eps) == 2)

    f = eps[0]["ficha"]
    comprobar("El RSS ya trae el titulo", f["titulo"] == "MAR 540. Chris Claremont y los X-Men")
    comprobar("El RSS ya trae la portada", f["portada"].endswith("portada_XXL.jpg"))
    comprobar("El RSS ya trae la duracion", f["duracion"] == "2 h 2 min",
              f"salio {f['duracion']!r}")
    comprobar("Los acentos y las eñes llegan enteros",
              f["descripcion"].startswith("Prepárate: una descripción con acentos, eñes"),
              f"salió {f['descripcion'][:60]!r}")
    comprobar("Y tambien limpia los dibujos de puntitos",
              "⣿" not in f["descripcion"] and "segunda linea" in f["descripcion"],
              f"salio {f['descripcion']!r}")
    comprobar("El episodio viene con la ficha hecha", eps[0]["ficha"] is not None)


def prueba_si_el_rss_falla_tira_de_la_web():
    """Noviembre 2026: iVoox devolvia 502 a GitHub. Que no se quede sin plan B."""
    def descargar(url):
        if "feeds.ivoox.com" in url:
            raise RuntimeError("502 Server Error: Bad Gateway")
        return PAGINA_DE_PODCAST
    ivoox._descargar = descargar

    eps = ivoox.episodios_visibles("1315616")
    comprobar("Si el RSS falla, se lee la web",
              [e["id"] for e in eps] == [300, 299, 298], f"salio {[e['id'] for e in eps]}")
    comprobar("Y por la web la ficha se pide despues", eps[0]["ficha"] is None)


def prueba_si_el_rss_viene_vacio_tira_de_la_web():
    def descargar(url):
        if "feeds.ivoox.com" in url:
            return "<rss><channel><title>vacio</title></channel></rss>"
        return PAGINA_DE_PODCAST
    ivoox._descargar = descargar

    comprobar("Un RSS vacio tampoco nos deja tirados",
              len(ivoox.episodios_visibles("1315616")) == 3)


def prueba_el_rss_manda_cuando_va_bien():
    ivoox._descargar = lambda url: RSS if "feeds.ivoox.com" in url else PAGINA_DE_PODCAST
    eps = ivoox.episodios_visibles("1311035")
    comprobar("Si el RSS va bien, ni se toca la web", eps[0]["ficha"] is not None)


# ---------------------------------------------------------------------------
# 1. Leer la lista de episodios (el plan B)
# ---------------------------------------------------------------------------

def prueba_lista_de_episodios():
    ivoox._descargar = lambda url: PAGINA_DE_PODCAST
    episodios = ivoox.desde_la_web("1315616")

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
    comprobar("No se fía del nombre de iVoox: lo pone podcasts.py",
              ficha["podcast"] == "")
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
              ivoox.desde_la_web("1315616") == [])


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
    "emoji": "📺",
}


def prueba_mensaje():
    texto = telegram.formatear(EPISODIO)

    comprobar("El nombre del podcast va arriba, con su emoji al lado",
              texto.startswith("🎙️ <b>El Aftershow</b> 📺"),
              f"salió {texto.splitlines()[0]!r}")

    sin_emoji = telegram.formatear(dict(EPISODIO, emoji=""))
    comprobar("Sin emoji propio, sale solo el micrófono",
              sin_emoji.startswith("🎙️ <b>El Aftershow</b>\n"))
    comprobar("Los signos raros del título no rompen el mensaje",
              "&lt;con un signo raro&gt;" in texto)
    comprobar("Sale la duración", "1 h 5 min" in texto)

    gigante = dict(EPISODIO, descripcion="x" * 5000)
    comprobar("Nunca pasa del límite de Telegram",
              len(telegram.formatear(gigante)) <= telegram.LIMITE_PIE_DE_FOTO,
              f"salió {len(telegram.formatear(gigante))}")


def prueba_el_nombre_lo_ponemos_nosotros():
    """iVoox devuelve "Marcianos en un Tren." con punto final. Usamos el nuestro."""
    ivoox._descargar = lambda url: pagina_de_episodio("Un episodio")
    ficha = ivoox.detalle("https://ejemplo", "1315616")

    # Así es como lo hace main.py: el nombre bueno es el de podcasts.py.
    ficha["podcast"] = "Marcianos en un Tren"
    ficha["emoji"] = "🚂"

    comprobar("El nombre sale como lo tenemos escrito nosotros",
              telegram.formatear(ficha).startswith("🎙️ <b>Marcianos en un Tren</b> 🚂"),
              f"salió {telegram.formatear(ficha).splitlines()[0]!r}")


def prueba_botones():
    todo = dict(EPISODIO, apple="https://apple/ep", podimo="https://podimo/x")
    filas = telegram.botones(todo)["inline_keyboard"]

    comprobar("iVoox va solo, arriba, a todo lo ancho",
              len(filas[0]) == 1 and "iVoox" in filas[0][0]["text"])
    comprobar("Debajo salen Apple, Spotify y Podimo, en ese orden",
              [b["text"].split()[-1] for b in filas[1]] == ["Apple", "Spotify", "Podimo"],
              f"salió {[b['text'] for b in filas[1]]}")

    solo_apple = telegram.botones(dict(todo, spotify="", podimo=""))["inline_keyboard"]
    comprobar("Lo que no está relleno no saca botón",
              [b["text"].split()[-1] for b in solo_apple[1]] == ["Apple"])

    nada = telegram.botones(dict(EPISODIO, spotify=""))["inline_keyboard"]
    comprobar("Si solo está en iVoox, una sola fila", len(nada) == 1)


def prueba_episodio_de_mecenas():
    """Los de pago: se avisa, pero marcado y con iVoox como único botón."""
    aviso = ("<a href='https://go.ivoox.com/rf/1'>Agradece a este podcast tantas horas de "
             "entretenimiento y disfruta de episodios exclusivos como éste. "
             "¡Apóyale en iVoox!</a> Volvemos a subirnos al vagón.")

    comprobar("Reconoce un episodio de pago", ivoox.es_de_pago(aviso))
    comprobar("Y no confunde uno normal",
              not ivoox.es_de_pago("Apóyanos en iVoox si te gusta el programa."))
    comprobar("Le quita la frase de iVoox a la descripción",
              ivoox.limpiar(ivoox.sin_aviso_de_pago(aviso)) == "Volvemos a subirnos al vagón.",
              f"salió {ivoox.limpiar(ivoox.sin_aviso_de_pago(aviso))!r}")

    de_pago = dict(EPISODIO, de_pago=True, apple="https://apple/ep")
    filas = telegram.botones(de_pago)["inline_keyboard"]
    comprobar("Un episodio de mecenas solo lleva el botón de iVoox",
              len(filas) == 1 and len(filas[0]) == 1 and "iVoox" in filas[0][0]["text"])
    comprobar("Y el mensaje avisa de que es para mecenas",
              "mecenas" in telegram.formatear(de_pago))
    comprobar("Uno normal no lleva ese aviso",
              "mecenas" not in telegram.formatear(EPISODIO))

    enlaces = main.donde_mas_escucharlo(
        {"apple": "123", "spotify": "s", "podimo": "p"}, {"id": 1}, {"de_pago": True})
    comprobar("Para uno de pago ni se molesta en preguntar a Apple",
              enlaces == {"apple": "", "spotify": "", "podimo": ""})


class _RespuestaFalsa:
    def __init__(self, datos=None, falla=False):
        self._datos, self._falla = datos or {}, falla
    def raise_for_status(self):
        if self._falla:
            raise RuntimeError("503")
    def json(self):
        return self._datos


def prueba_apple():
    original = apple.requests.get
    lista = {"results": [
        {"wrapperType": "track", "collectionId": 1164300225},
        {"wrapperType": "podcastEpisode", "episodeGuid": "https://www.ivoox.com/183685072",
         "trackViewUrl": "https://podcasts.apple.com/es/podcast/hackers-01/id1164300225?i=1000"},
        {"wrapperType": "podcastEpisode", "episodeGuid": "https://www.ivoox.com/18368507",
         "trackViewUrl": "https://podcasts.apple.com/es/podcast/otro/id1164300225?i=2000"},
    ]}
    try:
        apple.requests.get = lambda *a, **k: _RespuestaFalsa(lista)
        comprobar("Apple: encuentra el enlace directo al episodio",
                  apple.enlace("1164300225", 183685072).endswith("?i=1000"))
        comprobar("Apple: no confunde 18368507 con 183685072",
                  apple.enlace("1164300225", 18368507).endswith("?i=2000"))
        comprobar("Apple: si aún no lo tiene, enlaza al programa",
                  apple.enlace("1164300225", 999) ==
                  "https://podcasts.apple.com/es/podcast/id1164300225")

        apple.requests.get = lambda *a, **k: _RespuestaFalsa(falla=True)
        comprobar("Apple: si su buscador se cae, enlaza al programa y no rompe nada",
                  apple.enlace("1164300225", 183685072) ==
                  "https://podcasts.apple.com/es/podcast/id1164300225")
    finally:
        apple.requests.get = original


def prueba_reintento_de_descarga():
    """Si iVoox falla una vez, se prueba otra antes de rendirse."""
    original_get, original_pausa = ivoox.requests.get, ivoox.PAUSA_ANTES_DE_REINTENTAR
    llamadas = []

    class _Texto(_RespuestaFalsa):
        encoding = "utf-8"
        text = "hola"

    def a_la_segunda(*a, **k):
        llamadas.append(1)
        return _Texto(falla=len(llamadas) == 1)

    try:
        ivoox.PAUSA_ANTES_DE_REINTENTAR = 0
        ivoox.requests.get = a_la_segunda
        comprobar("Si iVoox falla una vez, lo intenta otra y sale",
                  _DESCARGAR_DE_VERDAD("https://ejemplo") == "hola" and len(llamadas) == 2)

        ivoox.requests.get = lambda *a, **k: _Texto(falla=True)
        try:
            _DESCARGAR_DE_VERDAD("https://ejemplo")
            comprobar("Si falla dos veces seguidas, avisa del fallo", False)
        except RuntimeError:
            comprobar("Si falla dos veces seguidas, avisa del fallo", True)
    finally:
        ivoox.requests.get, ivoox.PAUSA_ANTES_DE_REINTENTAR = original_get, original_pausa


# ---------------------------------------------------------------------------
# 5. La memoria: qué avisa y qué no
# ---------------------------------------------------------------------------

def _eps(pares):
    """pares = [(id, dias_de_antiguedad), ...]"""
    ahora = datetime.now(timezone.utc)
    return [{"id": i, "url": f"https://ejemplo/{i}", "ficha": {"t": i},
             "fecha": None if d is None else ahora - timedelta(days=d)}
            for i, d in pares]


def prueba_estreno_silencioso():
    ivoox.episodios_visibles = lambda i: _eps([(300, 0), (299, 7), (298, 14)])
    estado = {"avisados": [], "conocidos": []}

    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("La primera vez no avisa de nada", nuevos == [] and es_estreno)
    comprobar("Pero apunta los tres", sorted(estado["avisados"]) == [298, 299, 300])


def prueba_podcast_recien_añadido():
    """Añadir un programa a la lista no debe soltar de golpe sus episodios recientes."""
    ivoox.episodios_visibles = lambda i: _eps([(900, 0), (899, 3), (898, 6)])
    estado = {"avisados": [1, 2, 3], "conocidos": ["otro"]}   # el bot ya llevaba tiempo

    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "nuevo"}, estado)

    comprobar("Un podcast recién añadido entra en silencio", nuevos == [] and es_estreno)
    comprobar("Y queda apuntado como conocido", "nuevo" in estado["conocidos"])

    ivoox.episodios_visibles = lambda i: _eps([(901, 0), (900, 1)])
    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "nuevo"}, estado)
    comprobar("A partir de ahí, lo siguiente que publique sí se avisa",
              [e["id"] for e in nuevos] == [901] and not es_estreno)


def prueba_estado_sin_conocidos(tmp="estado_de_prueba.json"):
    """El estado.json de antes no traía 'conocidos'. Que no lo tome por estreno."""
    import os
    with open(tmp, "w", encoding="utf-8") as a:
        a.write('{"avisados": [1, 2, 3]}')
    antes = main.ARCHIVO_ESTADO
    main.ARCHIVO_ESTADO = tmp
    try:
        estado = main.cargar_estado()
        de_la_lista = [p["id_ivoox"] for p in main.podcasts.PODCASTS]
        comprobar("Un estado sin 'conocidos' da por conocidos los podcasts de hoy",
                  estado["conocidos"] == de_la_lista)
        main.guardar_estado(estado)
        comprobar("Y al guardar ya lo deja escrito",
                  main.cargar_estado()["conocidos"] == de_la_lista)
    finally:
        main.ARCHIVO_ESTADO = antes
        os.remove(tmp)


def prueba_modo_estreno():
    ivoox.episodios_visibles = lambda i: _eps([(300, 0), (299, 7), (298, 14)])
    estado = {"avisados": [], "conocidos": []}

    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "x"}, estado, estrenar=True)

    comprobar("En modo estreno publica el último", [e["id"] for e in nuevos] == [300])
    comprobar("Y no lo trata como estreno silencioso", es_estreno is False)


def prueba_episodio_nuevo():
    ivoox.episodios_visibles = lambda i: _eps([(302, 0), (301, 1), (300, 8)])
    estado = {"avisados": [300], "conocidos": ["x"]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Avisa solo de lo que no había visto",
              [e["id"] for e in nuevos] == [301, 302], f"salió {[e['id'] for e in nuevos]}")
    comprobar("Y en orden: primero el más viejo", nuevos[0]["id"] == 301)


def prueba_el_caso_del_mar_537():
    """El fallo real de octubre de 2026, que nos costó un episodio.

    MAR 536 salió el 8 oct con el número 181850904.
    MAR 537 salió el 15 oct con el número 181699760, MÁS BAJO.
    Con la regla vieja del "número más alto gana", el 537 nunca se publicó.
    """
    ivoox.episodios_visibles = lambda i: [
        {"id": 181699760, "url": "u537", "ficha": {}, "fecha": _hace(1)},   # MAR 537
        {"id": 181850904, "url": "u536", "ficha": {}, "fecha": _hace(8)},   # MAR 536
    ]
    estado = {"avisados": [181850904], "conocidos": ["x"]}   # del 536 ya avisamos

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Un episodio con número MÁS BAJO que el anterior sí se avisa",
              [e["id"] for e in nuevos] == [181699760],
              f"salió {[e['id'] for e in nuevos]}")


def _hace(dias):
    return datetime.now(timezone.utc) - timedelta(days=dias)


def prueba_no_resucita_lo_viejo():
    """Si iVoox reordena su catálogo, que no nos llegue un aviso de 2019."""
    ivoox.episodios_visibles = lambda i: _eps([(500, 0), (499, 400)])
    estado = {"avisados": [1], "conocidos": ["x"]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Lo de hace un año no se avisa", [e["id"] for e in nuevos] == [500])
    comprobar("Pero se da por visto, para no mirarlo cada vez",
              499 in estado["avisados"])


def prueba_sin_fecha_se_avisa():
    """Por la web no hay fecha. Mejor avisar de más que callarse."""
    ivoox.episodios_visibles = lambda i: _eps([(600, None)])
    estado = {"avisados": [1], "conocidos": ["x"]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)
    comprobar("Sin fecha, se avisa igual", [e["id"] for e in nuevos] == [600])


def prueba_nada_nuevo():
    ivoox.episodios_visibles = lambda i: _eps([(300, 1), (299, 8)])
    estado = {"avisados": [300, 299], "conocidos": ["x"]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)
    comprobar("Si no hay nada nuevo, no avisa", nuevos == [])


def prueba_guardian_de_avalanchas():
    ivoox.episodios_visibles = lambda i: _eps([(n, 0) for n in range(310, 300, -1)])
    estado = {"avisados": [1], "conocidos": ["x"]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Con diez de golpe, avisa solo del último",
              [e["id"] for e in nuevos] == [310], f"salió {[e['id'] for e in nuevos]}")
    comprobar("Y da los otros nueve por vistos", 309 in estado["avisados"])


def prueba_lo_que_se_anuncia_no_se_apunta_hasta_enviarlo():
    """Si Telegram falla, hay que reintentarlo en la pasada siguiente."""
    ivoox.episodios_visibles = lambda i: _eps([(700, 0)])
    estado = {"avisados": [1], "conocidos": ["x"]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("El episodio a anunciar NO queda apuntado todavía",
              700 not in estado["avisados"] and [e["id"] for e in nuevos] == [700])
    main.apuntar(estado, nuevos)
    comprobar("Se apunta cuando el mensaje ya ha salido", 700 in estado["avisados"])


def prueba_la_memoria_no_crece():
    estado = {"avisados": list(range(5000)), "conocidos": ["x"]}
    guardado = json.dumps({"avisados": estado["avisados"][-main.CUANTOS_RECORDAMOS:]})

    comprobar("El estado se queda en unos pocos kB",
              len(guardado) < 4000, f"salió {len(guardado)} bytes")
    comprobar("Y conserva los más recientes",
              estado["avisados"][-main.CUANTOS_RECORDAMOS:][-1] == 4999)


def prueba_estado_viejo_no_rompe(tmp="estado_viejo_de_prueba.json"):
    """El archivo del formato antiguo no debe reventar ni soltar una avalancha."""
    import os
    with open(tmp, "w", encoding="utf-8") as a:
        a.write('{"ultimos": {"1311035": 182953194}}')
    antes = main.ARCHIVO_ESTADO
    main.ARCHIVO_ESTADO = tmp
    try:
        estado = main.cargar_estado()
        comprobar("Un estado.json del formato viejo se lee sin romperse",
                  estado == {"avisados": [], "conocidos": []})
    finally:
        main.ARCHIVO_ESTADO = antes
        os.remove(tmp)


def prueba_ensayo_general(tmp="estado_de_ensayo.json"):
    """
    Una pasada completa de principio a fin, con iVoox, Apple y Telegram de
    mentira. Las pruebas de arriba miran cada pieza suelta; esta comprueba que
    encajan: que lo que sale del RSS llega a Telegram con sus botones y que el
    estado queda bien guardado.
    """
    import os
    hoy = email.utils.format_datetime(datetime.now(timezone.utc))
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0"><channel>
  <item><title>HACKERS 01. Cyberpunk</title>
    <link>https://www.ivoox.com/hackers-audios-mp3_rf_502_1.html</link>
    <description>Un episodio normal, con acentos: megacorporación.</description>
    <pubDate>{hoy}</pubDate><itunes:duration>01:46:36</itunes:duration>
    <itunes:image href="https://static-1.ivoox.com/p502.jpg"/></item>
  <item><title>VISIONWAGON 04 - Episodio exclusivo para mecenas</title>
    <link>https://www.ivoox.com/vision-audios-mp3_rf_501_1.html</link>
    <description>&lt;a href='https://go.ivoox.com/rf/501'&gt;Agradece a este podcast tantas horas de entretenimiento y disfruta de episodios exclusivos como éste. ¡Apóyale en iVoox!&lt;/a&gt; Volvemos al vagón.</description>
    <pubDate>{hoy}</pubDate><itunes:duration>39:36</itunes:duration>
    <itunes:image href="https://static-1.ivoox.com/p501.jpg"/></item>
  <item><title>Uno viejo ya avisado</title>
    <link>https://www.ivoox.com/viejo-audios-mp3_rf_500_1.html</link>
    <description>x</description><pubDate>{hoy}</pubDate></item>
</channel></rss>"""

    enviados = []

    def telegram_de_mentira(metodo, datos):
        enviados.append((metodo, datos))
        return {"message_id": len(enviados)}

    guardado = (main.ARCHIVO_ESTADO, main.podcasts.PODCASTS, main.sys.argv, main.time.sleep,
                ivoox._descargar, ivoox.episodios_visibles, apple.requests.get,
                telegram._llamar, dict(os.environ))
    try:
        main.ARCHIVO_ESTADO = tmp
        with open(tmp, "w", encoding="utf-8") as a:
            json.dump({"avisados": [500], "conocidos": ["77"]}, a)
        main.podcasts.PODCASTS = [{"nombre": "El Aftershow", "id_ivoox": "77", "emoji": "📺",
                                   "apple": "123", "spotify": "https://spotify/x",
                                   "podimo": "https://podimo/x"}]
        main.sys.argv = ["main.py"]
        main.time.sleep = lambda s: None
        ivoox._descargar = lambda url: feed
        ivoox.episodios_visibles = _EPISODIOS_VISIBLES_DE_VERDAD
        apple.requests.get = lambda *a, **k: _RespuestaFalsa({"results": [
            {"wrapperType": "podcastEpisode", "episodeGuid": "https://www.ivoox.com/502",
             "trackViewUrl": "https://podcasts.apple.com/es/podcast/hackers/id123?i=9"}]})
        telegram._llamar = telegram_de_mentira
        os.environ.update(TELEGRAM_TOKEN="x", TELEGRAM_CANAL="@difusion",
                          TELEGRAM_CANAL_CHAT="@charla")

        with contextlib.redirect_stdout(io.StringIO()):
            salida = main.main()

        fotos = [d for m_, d in enviados if m_ == "sendPhoto"]
        anclas = [d for m_, d in enviados if m_ == "pinChatMessage"]
        comprobar("Ensayo: la pasada termina bien", salida == 0)
        comprobar("Ensayo: dos episodios × dos canales = cuatro mensajes", len(fotos) == 4,
                  f"salieron {len(fotos)}")
        comprobar("Ensayo: se ancla en el canal de charla, y en silencio",
                  len(anclas) == 2 and all(a["chat_id"] == "@charla"
                                           and a["disable_notification"] for a in anclas))

        normal = next(d for d in fotos if "HACKERS" in d["caption"])
        de_pago = next(d for d in fotos if "VISIONWAGON" in d["caption"])
        textos = [b["text"] for fila in normal["reply_markup"]["inline_keyboard"] for b in fila]
        urls = [b["url"] for fila in normal["reply_markup"]["inline_keyboard"] for b in fila]
        comprobar("Ensayo: el episodio normal sale con sus cuatro botones", len(textos) == 4,
                  f"salió {textos}")
        comprobar("Ensayo: el botón de Apple va directo al episodio",
                  "https://podcasts.apple.com/es/podcast/hackers/id123?i=9" in urls)
        comprobar("Ensayo: los acentos llegan enteros a Telegram",
                  "megacorporación" in normal["caption"])
        comprobar("Ensayo: el de mecenas va marcado y solo con iVoox",
                  "mecenas</i>" in de_pago["caption"]
                  and len(de_pago["reply_markup"]["inline_keyboard"]) == 1
                  and "Agradece" not in de_pago["caption"])

        estado = main.cargar_estado()
        comprobar("Ensayo: los dos quedan apuntados para no repetirlos",
                  {500, 501, 502} <= set(estado["avisados"]))

        enviados.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            main.main()
        comprobar("Ensayo: una segunda pasada no repite nada", enviados == [])
    finally:
        (main.ARCHIVO_ESTADO, main.podcasts.PODCASTS, main.sys.argv, main.time.sleep,
         ivoox._descargar, ivoox.episodios_visibles, apple.requests.get,
         telegram._llamar, entorno) = guardado
        os.environ.clear(); os.environ.update(entorno)
        if os.path.exists(tmp):
            os.remove(tmp)


def todas():
    prueba_rss()
    prueba_si_el_rss_falla_tira_de_la_web()
    prueba_si_el_rss_viene_vacio_tira_de_la_web()
    prueba_el_rss_manda_cuando_va_bien()
    prueba_lista_de_episodios()
    prueba_ficha()
    prueba_ficha_de_otro_podcast()
    prueba_pagina_rota()
    prueba_duraciones()
    prueba_recorte()
    prueba_mensaje()
    prueba_el_nombre_lo_ponemos_nosotros()
    prueba_botones()
    prueba_episodio_de_mecenas()
    prueba_apple()
    prueba_reintento_de_descarga()
    prueba_estreno_silencioso()
    prueba_podcast_recien_añadido()
    prueba_estado_sin_conocidos()
    prueba_modo_estreno()
    prueba_el_caso_del_mar_537()
    prueba_no_resucita_lo_viejo()
    prueba_sin_fecha_se_avisa()
    prueba_lo_que_se_anuncia_no_se_apunta_hasta_enviarlo()
    prueba_estado_viejo_no_rompe()
    prueba_episodio_nuevo()
    prueba_nada_nuevo()
    prueba_guardian_de_avalanchas()
    prueba_la_memoria_no_crece()
    prueba_ensayo_general()


if __name__ == "__main__":
    todas()
    print()
    if fallos:
        print(f"❌ {len(fallos)} prueba(s) mal: {', '.join(fallos)}")
        sys.exit(1)
    print("🎉 Todo bien. Se puede subir.")
