"""
apple.py — Busca un episodio en Apple Podcasts.

Apple tiene un buscador público y gratuito. Le decimos "enséñame los últimos
episodios de este programa" y miramos si entre ellos está el nuestro. Lo
reconocemos porque Apple guarda, de cada episodio, la dirección original de
iVoox, que acaba en el mismo número que usamos nosotros:

    https://www.ivoox.com/183685072

Si lo encuentra, devolvemos el enlace DIRECTO al episodio. Si no (Apple tarda
unas horas en enterarse de los episodios nuevos, o su buscador no contesta),
devolvemos el enlace al programa, donde el episodio aparecerá arriba del todo
en cuanto Apple lo recoja. Pase lo que pase, el botón lleva a un sitio que sirve.
"""

import requests

BUSCADOR = "https://itunes.apple.com/lookup"
PROGRAMA = "https://podcasts.apple.com/es/podcast/id{id_apple}"

TIEMPO_MAXIMO = 15  # segundos. Si Apple va lenta, no nos quedamos esperando.


def enlace(id_apple, numero_de_episodio):
    """Devuelve el mejor enlace que tengamos de este episodio en Apple Podcasts."""
    programa = PROGRAMA.format(id_apple=id_apple)

    try:
        respuesta = requests.get(
            BUSCADOR,
            params={"id": id_apple, "entity": "podcastEpisode",
                    "limit": 25, "country": "ES"},
            timeout=TIEMPO_MAXIMO,
        )
        respuesta.raise_for_status()

        for cosa in respuesta.json().get("results", []):
            if cosa.get("wrapperType") != "podcastEpisode":
                continue
            origen = str(cosa.get("episodeGuid") or "").rstrip("/")
            if origen.endswith("/" + str(numero_de_episodio)) and cosa.get("trackViewUrl"):
                return cosa["trackViewUrl"]

        print("   ↳ Apple todavía no tiene el episodio; enlazo al programa.")

    except Exception as error:
        print(f"   ↳ Apple no contesta ({type(error).__name__}); enlazo al programa.")

    return programa
