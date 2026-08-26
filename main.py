"""
main.py — El director de orquesta.

Lo que hace, en orden:
  1. Mira la web de cada podcast de la lista (podcasts.py).
  2. Compara con estado.json, donde guardamos el número del último episodio
     del que ya avisamos.
  3. De lo que sea nuevo, lee la ficha y lo publica en Telegram.
  4. Apunta hasta dónde ha llegado.

Formas de ejecutarlo:
  python main.py            → funcionamiento normal
  python main.py --prueba   → manda un mensaje de mentira, para ver que Telegram va
  python main.py --seco     → mira las webs y enseña qué haría, SIN publicar nada
  python main.py --estreno  → para el día que estrenas canal: publica el último
                              episodio de cada podcast para que no quede vacío
"""

import json
import os
import sys
import time
import traceback

import ivoox
import podcasts
import telegram

ARCHIVO_ESTADO = "estado.json"

# Si un podcast aparece de golpe con más episodios nuevos que esto, algo raro
# pasa (iVoox ha rediseñado la web, o hemos estado semanas parados). En vez de
# soltar quince mensajes seguidos, avisamos solo del último y apuntamos el resto
# en silencio.
MAXIMO_AVISOS_DE_GOLPE = 4


# ---------------------------------------------------------------------------
# La memoria
# ---------------------------------------------------------------------------
# estado.json es diminuto y no crece nunca. Guarda una sola cosa por podcast:
# el número del episodio más nuevo del que ya hemos avisado.
#
#   {"ultimos": {"1315616": 179260903, "1311035": 179082223}}

def cargar_estado():
    if not os.path.exists(ARCHIVO_ESTADO):
        return {"ultimos": {}}
    try:
        with open(ARCHIVO_ESTADO, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        datos.setdefault("ultimos", {})
        return datos
    except Exception:
        print("⚠️  estado.json ilegible. Empiezo de cero: esta vez no aviso de nada.")
        return {"ultimos": {}}


def guardar_estado(estado):
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as archivo:
        json.dump({"ultimos": estado["ultimos"]}, archivo,
                  ensure_ascii=False, indent=1, sort_keys=True)


# ---------------------------------------------------------------------------
# El trabajo
# ---------------------------------------------------------------------------

def episodios_nuevos_de(podcast, estado, estrenar=False):
    """
    Devuelve los episodios nuevos de un podcast, del más viejo al más nuevo,
    y si es la primera vez que lo miramos.

    Con estrenar=True, la primera vez que vemos un podcast publicamos su último
    episodio en vez de callarnos. Es para el día que abres el canal y no quieres
    que se quede vacío hasta el siguiente programa.
    """
    id_ivoox = podcast["id_ivoox"]
    visibles = ivoox.episodios_visibles(id_ivoox)

    if not visibles:
        raise RuntimeError("no he encontrado ni un episodio (¿ha cambiado la web?)")

    ultimo_avisado = estado["ultimos"].get(id_ivoox)

    # Primera vez que vemos este podcast: apuntamos dónde está y NO avisamos.
    # Si no, el primer día llegarían cientos de mensajes con episodios viejos.
    if ultimo_avisado is None:
        if estrenar:
            # Damos por vistos todos menos el último, que sí publicamos.
            anterior = visibles[1]["id"] if len(visibles) > 1 else visibles[0]["id"] - 1
            estado["ultimos"][id_ivoox] = anterior
            return [visibles[0]], False

        estado["ultimos"][id_ivoox] = visibles[0]["id"]
        return [], True

    nuevos = [e for e in visibles if e["id"] > ultimo_avisado]
    nuevos.reverse()  # del más viejo al más nuevo, que es el orden natural

    if len(nuevos) > MAXIMO_AVISOS_DE_GOLPE:
        print(f"   ⚠️  {len(nuevos)} episodios nuevos de golpe. Aviso solo del último "
              f"y apunto los demás en silencio.")
        estado["ultimos"][id_ivoox] = nuevos[-2]["id"]
        nuevos = nuevos[-1:]

    return nuevos, False


def main():
    if "--prueba" in sys.argv:
        print("Enviando mensaje de prueba…")
        telegram.publicar({
            "podcast": "Mensaje de prueba",
            "titulo": "Si lees esto, el bot funciona",
            "descripcion": "Esto no es un episodio de verdad. Es el bot diciendo hola.",
            "duracion": "0 min",
            "portada": "",
            "url": "https://www.ivoox.com",
            "spotify": "",
            "emoji": "🤖",
        })
        return 0

    modo_seco = "--seco" in sys.argv
    modo_estreno = "--estreno" in sys.argv
    estado = cargar_estado()

    if modo_estreno:
        print("🎬 Modo estreno: de los podcasts que vea por primera vez, publico su "
              "último episodio.\n")

    algo_ha_respondido = False
    publicados = 0

    for podcast in podcasts.PODCASTS:
        nombre = podcast["nombre"]
        print(f"\n🔎 {nombre}")

        try:
            nuevos, es_estreno = episodios_nuevos_de(podcast, estado, modo_estreno)
            algo_ha_respondido = True
        except Exception as error:
            print(f"   ❌ {type(error).__name__}: {error}")
            continue

        if es_estreno:
            print(f"   🌱 primera vez que lo miro. Apunto dónde está y no aviso de nada.")
            continue

        if not nuevos:
            print("   😴 nada nuevo.")
            continue

        print(f"   🎉 {len(nuevos)} episodio(s) nuevo(s)")

        for episodio in nuevos:
            try:
                ficha = ivoox.detalle(episodio["url"], podcast["id_ivoox"])
            except Exception as error:
                print(f"   ❌ no he podido leer {episodio['url']}: {error}")
                print("      Lo dejo para la próxima vez.")
                break  # no avanzamos el marcador: se reintenta en la siguiente pasada

            if ficha is None:
                print(f"   ↷ {episodio['id']} no es de este podcast (recomendado). Lo salto.")
                estado["ultimos"][podcast["id_ivoox"]] = episodio["id"]
                continue

            # El nombre lo ponemos NOSOTROS, el de podcasts.py. El que devuelve
            # iVoox viene tal cual lo tenga la ficha y a veces trae cosas raras
            # (el de Marcianos, por ejemplo, lleva un punto final: "Marcianos en
            # un Tren."). Así el mensaje sale siempre igual y tú lo controlas.
            ficha["podcast"] = nombre
            ficha["spotify"] = podcast.get("spotify", "")
            ficha["emoji"] = podcast.get("emoji", "")

            print(f"   · {ficha['titulo'][:70]}")

            if modo_seco:
                estado["ultimos"][podcast["id_ivoox"]] = episodio["id"]
                continue

            if telegram.publicar(ficha):
                publicados += 1
                estado["ultimos"][podcast["id_ivoox"]] = episodio["id"]
                time.sleep(2)
            else:
                print("      No ha salido. Lo dejo para la próxima vez.")
                break

        time.sleep(1)  # un respiro entre podcasts, por educación

    if not algo_ha_respondido:
        print("\n❌ Ningún podcast ha respondido. No toco el estado; ya lo reintentaré.")
        return 1

    if modo_seco:
        print("\n(modo --seco: no he publicado nada ni he guardado el estado)")
        return 0

    guardar_estado(estado)
    print(f"\n✅ Listo. {publicados} publicación(es).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
