"""
podcasts.py — La lista de podcasts que vigila el bot.

Este es el ÚNICO archivo que vas a querer tocar cuando cambie algo.

Para AÑADIR un podcast:
  1. Abre su página en iVoox. La dirección acaba en algo como
         .../podcast-lo-que-sea_sq_f1315616_1.html
     Ese número de después de "_sq_f" es el identificador. Aquí sería 1315616.
  2. Copia una línea de las de abajo y cambia el nombre y el identificador.
  3. Si el podcast está en Spotify, pega también el enlace. Si no, deja "".
  4. Elige su emoji: es el que sale al lado del nombre en el mensaje, para que se
     distinga de un vistazo. Si lo dejas "", sale solo el micrófono.

Para QUITAR un podcast: borra su línea (o ponle un # delante).
"""

PODCASTS = [
    {
        "nombre": "El Aftershow",
        "id_ivoox": "1315616",
        "emoji": "📺",
        "spotify": "https://open.spotify.com/show/0xCmZRg7v5NIg9VObE8AcM",
    },
    {
        "nombre": "Marcianos en un Tren",
        "id_ivoox": "1311035",
        "emoji": "🚂",
        # En Spotify, Marcianos se quedó parado en 2025, así que el botón mandaría
        # a la gente a un sitio sin el episodio. Si algún día se arregla, pega aquí
        # https://open.spotify.com/show/2E6LAFwZy5HoQm7JkEoKav
        "spotify": "",
    },
    {
        "nombre": "Jugones",
        "id_ivoox": "11085022",
        "emoji": "👾",
        "spotify": "",   # no lo he encontrado en Spotify; si lo tienes, pégalo aquí
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
#      "spotify": "https://open.spotify.com/show/0GjIkkroTBJGMaZDv0cYs8"},
#
# Área 51: es el canal de contenido de pago. Café para cafeteros, y tiene su
# propio sitio donde avisar.
#
#     {"nombre": "Área 51", "id_ivoox": "11164201", "emoji": "🛸", "spotify": ""},
