"""
main.py — El director de orquesta.

Lo que hace, en orden:
  1. Mira el RSS de cada podcast de la lista (podcasts.py); si el RSS
     falla, su página web.
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
from datetime import datetime, timedelta, timezone
import sys
import time
import traceback

import ivoox
import podcasts
import telegram

ARCHIVO_ESTADO = "estado.json"

# Si de golpe hay más episodios nuevos que esto, algo raro pasa. En vez de soltar
# quince mensajes seguidos, avisamos solo del último y apuntamos el resto en silencio.
MAXIMO_AVISOS_DE_GOLPE = 4

# No avisamos de episodios más viejos que esto. Es la red de seguridad por si
# iVoox reordena su catálogo o resucita algo antiguo: que no te llegue de madrugada
# un aviso de un programa de hace dos años.
DIAS_DE_GRACIA = 10

# Cuántos episodios recordamos. Con esto hay de sobra para no repetir nada, y el
# archivo se queda en unos pocos kilobytes para siempre.
CUANTOS_RECORDAMOS = 400


# ---------------------------------------------------------------------------
# La memoria
# ---------------------------------------------------------------------------
# estado.json guarda la LISTA de episodios de los que ya hemos avisado:
#
#   {"avisados": [182949557, 182953194, ...]}
#
# Antes guardábamos solo el número más alto, dando por hecho que los números
# van siempre a más. NO ES VERDAD, y nos costó un episodio:
#
#   MAR 536  salió el  8 oct  con el número 181850904
#   MAR 537  salió el 15 oct  con el número 181699760   ← ¡más bajo!
#
# iVoox pone el número cuando SUBES el episodio, no cuando se publica. Como Xevi
# los deja programados con antelación, uno grabado antes puede salir después y
# llevar un número menor. Con la regla del "más alto gana", el MAR 537 se dio por
# visto sin haberse publicado nunca. Por eso ahora guardamos la lista entera.

def cargar_estado():
    if not os.path.exists(ARCHIVO_ESTADO):
        return {"avisados": []}
    try:
        with open(ARCHIVO_ESTADO, encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except Exception:
        print("⚠️  estado.json ilegible. Empiezo de cero: esta vez no aviso de nada.")
        return {"avisados": []}

    if "avisados" in datos:
        datos["avisados"] = [int(x) for x in datos["avisados"]]
        return datos

    # Archivo del formato viejo (el de "ultimos"): no sabemos de qué se avisó
    # exactamente, así que empezamos de cero y nos callamos esta vez.
    print("⚠️  estado.json es del formato viejo. Apunto lo que hay y no aviso de nada.")
    return {"avisados": []}


def guardar_estado(estado):
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as archivo:
        json.dump({"avisados": estado["avisados"][-CUANTOS_RECORDAMOS:]},
                  archivo, ensure_ascii=False, indent=1)


def apuntar(estado, episodios):
    """Da por vistos estos episodios, sin repetirlos ni perder el orden."""
    ya = set(estado["avisados"])
    for episodio in episodios:
        if episodio["id"] not in ya:
            estado["avisados"].append(episodio["id"])
            ya.add(episodio["id"])


def es_reciente(episodio):
    """¿Es de los últimos días? Si iVoox no da la fecha, lo damos por bueno."""
    if not episodio.get("fecha"):
        return True
    edad = datetime.now(timezone.utc) - episodio["fecha"]
    return edad <= timedelta(days=DIAS_DE_GRACIA)


# ---------------------------------------------------------------------------
# El trabajo
# ---------------------------------------------------------------------------

def episodios_nuevos_de(podcast, estado, estrenar=False):
    """
    Devuelve los episodios nuevos de un podcast, del más viejo al más nuevo,
    y si es la primera vez que lo miramos.
    """
    visibles = ivoox.episodios_visibles(podcast["id_ivoox"])

    if not visibles:
        raise RuntimeError("no he encontrado ni un episodio (¿ha cambiado la web?)")

    # Primera vez de todas: apuntamos lo que hay y NO avisamos. Si no, el primer
    # día llegarían cientos de mensajes con episodios viejos. (Con --estreno sí
    # sacamos el último de cada uno, para que un canal nuevo no nazca vacío.)
    if not estado["avisados"]:
        if estrenar:
            apuntar(estado, visibles[1:])
            return [visibles[0]], False
        apuntar(estado, visibles)
        return [], True

    ya = set(estado["avisados"])
    nuevos = [e for e in visibles if e["id"] not in ya and es_reciente(e)]

    # Del más viejo al más nuevo, que es el orden natural para leerlos.
    nuevos.sort(key=lambda e: (e["fecha"] is None, e["fecha"] or 0, e["id"]))

    if len(nuevos) > MAXIMO_AVISOS_DE_GOLPE:
        print(f"   ⚠️  {len(nuevos)} episodios nuevos de golpe. Aviso solo del último.")
        nuevos = nuevos[-1:]

    # Damos por vistos todos los que NO vamos a anunciar: los viejos y los que
    # ha descartado el guardián. De los que sí anunciamos se encarga main(),
    # cuando el mensaje haya salido de verdad: si Telegram falla, queremos
    # reintentarlo en la siguiente pasada, no darlo por hecho.
    a_anunciar = {e["id"] for e in nuevos}
    apuntar(estado, [e for e in visibles if e["id"] not in a_anunciar])

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
            # Si venimos del RSS la ficha ya está hecha. Si venimos de la web,
            # hay que pedir la página del episodio para sacarla.
            try:
                ficha = episodio.get("ficha") or ivoox.detalle(
                    episodio["url"], podcast["id_ivoox"])
            except Exception as error:
                print(f"   ❌ no he podido leer {episodio['url']}: {error}")
                print("      Lo dejo para la próxima vez.")
                break  # no avanzamos el marcador: se reintenta en la siguiente pasada

            if ficha is None:
                print(f"   ↷ {episodio['id']} no es de este podcast (recomendado). Lo salto.")
                apuntar(estado, [episodio])
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
                continue

            if telegram.publicar(ficha):
                publicados += 1
                apuntar(estado, [episodio])   # ya está fuera: no repetirlo
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
