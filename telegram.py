"""
telegram.py — Manda los mensajes y, si toca, los ancla.

Dos sitios distintos, y los dos son opcionales por separado:

  · TELEGRAM_CANAL       → el canal de difusión (@redmarcianapods).
  · TELEGRAM_CANAL_CHAT  → el canal/grupo de charla. Si lo pones, además de
                           publicar ahí, el bot ancla el mensaje.

Si no pones el segundo, el bot simplemente no lo usa y no pasa nada.
"""

import html
import os
import time

import requests

API = "https://api.telegram.org/bot{token}/{metodo}"

# Telegram no deja pasar de 1024 caracteres en el pie de una foto.
LIMITE_PIE_DE_FOTO = 1024

# El emoji que abre todos los mensajes. El de la derecha es distinto para cada
# podcast y se elige en podcasts.py.
EMOJI_DE_TODOS = "🎙️"


def _token():
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "❌ Falta el token del bot.\n"
            "   En GitHub: Settings → Secrets and variables → Actions → TELEGRAM_TOKEN"
        )
    return token


def canal_difusion():
    destino = os.environ.get("TELEGRAM_CANAL", "").strip()
    if not destino:
        raise SystemExit(
            "❌ Falta el canal donde publicar.\n"
            "   En GitHub: Settings → Secrets and variables → Actions → TELEGRAM_CANAL\n"
            "   (vale '@redmarcianapods' o el número que empieza por -100)"
        )
    return destino


def canal_chat():
    """El canal de charla. Devuelve '' si no está puesto, y no pasa nada."""
    return os.environ.get("TELEGRAM_CANAL_CHAT", "").strip()


def _llamar(metodo, datos):
    """Llama a Telegram. Devuelve la respuesta si va bien, o None si falla."""
    for intento in (1, 2, 3):
        try:
            respuesta = requests.post(
                API.format(token=_token(), metodo=metodo), json=datos, timeout=30
            )
            if respuesta.ok:
                return respuesta.json().get("result")

            detalle = respuesta.json().get("description", respuesta.text[:150])
            print(f"   ⚠️  {metodo}: intento {intento} fallido: {detalle}")

            # Reintentar estos no sirve de nada.
            if any(p in detalle.lower() for p in ("chat not found", "blocked", "not enough rights")):
                return None

        except Exception as error:
            print(f"   ⚠️  {metodo}: intento {intento} fallido: {error}")

        time.sleep(2 * intento)

    return None


# ---------------------------------------------------------------------------
# El mensaje bonito
# ---------------------------------------------------------------------------

def formatear(episodio):
    """Monta el texto que acompaña a la portada."""
    escapar = html.escape

    cabecera = f"{EMOJI_DE_TODOS} <b>{escapar(episodio['podcast'])}</b>"
    if episodio.get("emoji"):
        cabecera += f" {episodio['emoji']}"

    partes = [cabecera, ""]
    partes.append(f"<b>{escapar(episodio['titulo'])}</b>")

    if episodio.get("descripcion"):
        partes += ["", escapar(episodio["descripcion"])]

    if episodio.get("duracion"):
        partes += ["", f"⏱️ {escapar(episodio['duracion'])}"]

    texto = "\n".join(partes)

    # Por si acaso: si nos pasamos del límite, recortamos por el final.
    if len(texto) > LIMITE_PIE_DE_FOTO:
        texto = texto[: LIMITE_PIE_DE_FOTO - 1].rstrip() + "…"

    return texto


def botones(episodio):
    """Los botones de 'escuchar aquí' que van debajo del mensaje."""
    fila = [{"text": "▶️ Escuchar en iVoox", "url": episodio["url"]}]

    if episodio.get("spotify"):
        fila.append({"text": "🎧 Spotify", "url": episodio["spotify"]})

    return {"inline_keyboard": [fila]}


# ---------------------------------------------------------------------------
# Publicar
# ---------------------------------------------------------------------------

def _enviar_a(destino, episodio, anclar=False):
    """Publica el episodio en un chat. Si anclar=True, además lo ancla."""
    texto = formatear(episodio)
    teclado = botones(episodio)

    mensaje = None

    if episodio.get("portada"):
        mensaje = _llamar("sendPhoto", {
            "chat_id": destino,
            "photo": episodio["portada"],
            "caption": texto,
            "parse_mode": "HTML",
            "reply_markup": teclado,
        })

    # Si no hay portada, o si Telegram no ha podido con la imagen, va sin foto.
    if not mensaje:
        if episodio.get("portada"):
            print("   ↳ la portada ha dado problemas; lo mando sin foto.")
        mensaje = _llamar("sendMessage", {
            "chat_id": destino,
            "text": texto,
            "parse_mode": "HTML",
            "reply_markup": teclado,
            "disable_web_page_preview": True,
        })

    if not mensaje:
        print(f"   ❌ no he podido publicar en {destino}")
        return False

    print(f"   ✅ publicado en {destino}")

    if anclar:
        anclado = _llamar("pinChatMessage", {
            "chat_id": destino,
            "message_id": mensaje["message_id"],
            "disable_notification": True,
        })
        if anclado:
            print(f"   📌 anclado en {destino}")
        else:
            print(f"   ⚠️  no he podido anclar en {destino} "
                  f"(¿el bot es administrador con permiso para anclar?)")

    return True


def publicar(episodio):
    """Publica en el canal de difusión y, si está configurado, en el de charla."""
    ok = _enviar_a(canal_difusion(), episodio, anclar=False)

    chat = canal_chat()
    if chat:
        time.sleep(1)
        _enviar_a(chat, episodio, anclar=True)

    return ok
