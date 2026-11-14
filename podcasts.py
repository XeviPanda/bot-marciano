"""
podcasts.py — La lista de podcasts que vigila el bot.

Este es el ÚNICO archivo que vas a querer tocar cuando cambie algo.

Para AÑADIR un podcast:
  1. Abre su página en iVoox. La dirección acaba en algo como
         .../podcast-lo-que-sea_sq_f1315616_1.html
     Ese número de después de "_sq_f" es el identificador. Aquí sería 1315616.
  2. Copia uno de los bloques de abajo y cambia el nombre y el identificador.
  3. Elige su emoji: es el que sale al lado del nombre en el mensaje, para que se
     distinga de un vistazo. Si lo dejas "", sale solo el micrófono.
  4. Rellena dónde más se puede escuchar. Cada uno que rellenes es un botón
     debajo del mensaje; lo que dejes en "" no sale.

       "apple"   → el NÚMERO del programa en Apple Podcasts. Está en su dirección:
                   podcasts.apple.com/es/podcast/el-aftershow/id1164300225
                   (solo el número, sin el "id"). El bot busca él solo el enlace
                   directo al episodio.
       "spotify" → la dirección del programa en Spotify.
       "podimo"  → la dirección del programa en Podimo.

     Un aviso: pon solo sitios donde el programa esté AL DÍA. Un botón que lleva
     a un sitio donde el episodio no está es peor que no tener botón.

Para QUITAR un podcast: borra su línea (o ponle un # delante).
"""

PODCASTS = [
    {
        "nombre": "El Aftershow",
        "id_ivoox": "1315616",
        "emoji": "📺",
        "apple": "1164300225",
        "spotify": "https://open.spotify.com/show/0xCmZRg7v5NIg9VObE8AcM",
        "podimo": "https://podimo.com/es/shows/el-aftershow",
    },
    {
        "nombre": "Marcianos en un Tren",
        "id_ivoox": "1311035",
        "emoji": "🚂",
        "apple": "1164300358",
        # En Spotify, Marcianos lleva parado desde marzo de 2025 (comprobado otra
        # vez el 14 nov 2026: sigue en el MAR 457). Hasta que se arregle, sin botón.
        # El programa es https://open.spotify.com/show/2E6LAFwZy5HoQm7JkEoKav
        "spotify": "",
        "podimo": "https://podimo.com/es/shows/marcianos-en-un-tren",
    },
    {
        "nombre": "Jugones",
        "id_ivoox": "11085022",
        "emoji": "👾",
        "apple": "1565774482",
        "spotify": "",   # no está en Spotify
        "podimo": "",    # el "Jugones" que hay en Podimo es otro, de deportes
    },
]

# ---------------------------------------------------------------------------
# FUERA A PROPÓSITO
# ---------------------------------------------------------------------------
# Estos dos están apagados por decisión tuya, no porque fallen. Para volver a
# encenderlos, quítales las almohadillas y mételos dentro de la lista de arriba.
#
# Ficción Marciana: se publica en cuanto está listo, sin hora fija. Para pillarlo
# al vuelo habría que mirar cada pocos minutos, y no compensa. Lo pones tú a mano.
#
#     {"nombre": "Ficción Marciana", "id_ivoox": "1647387", "emoji": "📖",
#      "apple": "1448128173", "podimo": "",
#      "spotify": "https://open.spotify.com/show/0GjIkkroTBJGMaZDv0cYs8"},
#
# Área 51: es el canal de contenido de pago. Café para cafeteros, y tiene su
# propio sitio donde avisar.
#
#     {"nombre": "Área 51", "id_ivoox": "11164201", "emoji": "🛸",
#      "apple": "", "spotify": "", "podimo": ""},
