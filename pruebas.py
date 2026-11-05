"""
pruebas.py — Comprueba que el bot hace lo que creemos que hace.

Ejecútalo con:   python pruebas.py

No toca internet ni manda nada a Telegram: usa páginas de mentira escritas aquí
mismo. Si sale todo en verde, se puede subir con tranquilidad.
"""

import json
import sys
from datetime import datetime, timedelta, timezone

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
    con = telegram.botones(EPISODIO)
    comprobar("Con Spotify salen dos botones",
              len(con["inline_keyboard"][0]) == 2)

    sin = telegram.botones(dict(EPISODIO, spotify=""))
    comprobar("Sin Spotify sale solo el de iVoox",
              len(sin["inline_keyboard"][0]) == 1)


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
    estado = {"avisados": []}

    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("La primera vez no avisa de nada", nuevos == [] and es_estreno)
    comprobar("Pero apunta los tres", sorted(estado["avisados"]) == [298, 299, 300])


def prueba_modo_estreno():
    ivoox.episodios_visibles = lambda i: _eps([(300, 0), (299, 7), (298, 14)])
    estado = {"avisados": []}

    nuevos, es_estreno = main.episodios_nuevos_de({"id_ivoox": "x"}, estado, estrenar=True)

    comprobar("En modo estreno publica el último", [e["id"] for e in nuevos] == [300])
    comprobar("Y no lo trata como estreno silencioso", es_estreno is False)


def prueba_episodio_nuevo():
    ivoox.episodios_visibles = lambda i: _eps([(302, 0), (301, 1), (300, 8)])
    estado = {"avisados": [300]}

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
    estado = {"avisados": [181850904]}   # del 536 ya avisamos

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Un episodio con número MÁS BAJO que el anterior sí se avisa",
              [e["id"] for e in nuevos] == [181699760],
              f"salió {[e['id'] for e in nuevos]}")


def _hace(dias):
    return datetime.now(timezone.utc) - timedelta(days=dias)


def prueba_no_resucita_lo_viejo():
    """Si iVoox reordena su catálogo, que no nos llegue un aviso de 2019."""
    ivoox.episodios_visibles = lambda i: _eps([(500, 0), (499, 400)])
    estado = {"avisados": [1]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Lo de hace un año no se avisa", [e["id"] for e in nuevos] == [500])
    comprobar("Pero se da por visto, para no mirarlo cada vez",
              499 in estado["avisados"])


def prueba_sin_fecha_se_avisa():
    """Por la web no hay fecha. Mejor avisar de más que callarse."""
    ivoox.episodios_visibles = lambda i: _eps([(600, None)])
    estado = {"avisados": [1]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)
    comprobar("Sin fecha, se avisa igual", [e["id"] for e in nuevos] == [600])


def prueba_nada_nuevo():
    ivoox.episodios_visibles = lambda i: _eps([(300, 1), (299, 8)])
    estado = {"avisados": [300, 299]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)
    comprobar("Si no hay nada nuevo, no avisa", nuevos == [])


def prueba_guardian_de_avalanchas():
    ivoox.episodios_visibles = lambda i: _eps([(n, 0) for n in range(310, 300, -1)])
    estado = {"avisados": [1]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("Con diez de golpe, avisa solo del último",
              [e["id"] for e in nuevos] == [310], f"salió {[e['id'] for e in nuevos]}")
    comprobar("Y da los otros nueve por vistos", 309 in estado["avisados"])


def prueba_lo_que_se_anuncia_no_se_apunta_hasta_enviarlo():
    """Si Telegram falla, hay que reintentarlo en la pasada siguiente."""
    ivoox.episodios_visibles = lambda i: _eps([(700, 0)])
    estado = {"avisados": [1]}

    nuevos, _ = main.episodios_nuevos_de({"id_ivoox": "x"}, estado)

    comprobar("El episodio a anunciar NO queda apuntado todavía",
              700 not in estado["avisados"] and [e["id"] for e in nuevos] == [700])
    main.apuntar(estado, nuevos)
    comprobar("Se apunta cuando el mensaje ya ha salido", 700 in estado["avisados"])


def prueba_la_memoria_no_crece():
    estado = {"avisados": list(range(5000))}
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
                  estado == {"avisados": []})
    finally:
        main.ARCHIVO_ESTADO = antes
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
    prueba_estreno_silencioso()
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


if __name__ == "__main__":
    todas()
    print()
    if fallos:
        print(f"❌ {len(fallos)} prueba(s) mal: {', '.join(fallos)}")
        sys.exit(1)
    print("🎉 Todo bien. Se puede subir.")
