# Bot Marciano

Avisa en Telegram cuando Red Marciana publica un podcast nuevo.

Sustituye al viejo `@ivooxrssbot`, que dependía del RSS de iVoox. El **23 de agosto
de 2026** comprobamos que los feeds RSS de *El Aftershow* y *Marcianos en un Tren*
llevaban meses congelados (servían siempre los mismos 100 episodios) aunque en la
web seguían saliendo programas nuevos. Es un fallo de iVoox, no del bot. Por eso
este lee **la web**, que sí está al día.

## Dónde publica

| | |
|---|---|
| Canal de difusión | **@redmarcianapods** — nuevo, para empezar de cero |
| Canal de charla | **@redmarciana** — ahí publica *y ancla* el episodio |
| Bot | **@Paco_y_Federico_bot** |

El canal viejo, **@redmarcianarss**, se queda tal cual con todo lo anterior. Este
bot no lo toca.

---

## Montarlo, paso a paso

### 1. El repositorio: **público**

En GitHub, **New repository** → nombre a tu gusto → **Public** → *Create*.

Público a propósito, por dos razones: los repositorios públicos tienen **minutos de
GitHub Actions ilimitados** (los privados comparten un tope de 2.000 al mes, y ese
cupo lo quieres entero para el bot de One Piece), y aquí no hay nada que esconder.
Los *secrets* siguen siendo secretos aunque el repositorio se vea: **no salen en el
código ni en los registros**. La visibilidad es de cada repositorio por separado, así
que `den-den-mushi` sigue privado sin que esto le afecte.

Sube estos archivos respetando las carpetas:

```
main.py
ivoox.py
telegram.py
podcasts.py
pruebas.py
estado.json
requirements.txt
.github/workflows/check.yml     ← el archivo se llama check.yml
README.md
```

> ⚠️ Ojo con el editor web de GitHub: al crear un archivo nuevo va bien, pero al
> editar uno que ya existe **te destroza la sangría del `.yml`**. Si tienes que
> cambiar `check.yml`, bórralo y créalo otra vez.

### 2. Meter el bot en los canales

**@Paco_y_Federico_bot** ya está creado. Ahora, en cada canal:
Administrar → Administradores → Añadir administrador → busca el bot.

- En **@redmarcianapods**: con que pueda **publicar mensajes** ya vale.
- En **@redmarciana**: además, permiso para **anclar mensajes**.

### 3. Poner las contraseñas

En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**.

| Nombre | Qué va aquí |
|---|---|
| `TELEGRAM_TOKEN` | El token que te dio BotFather. Es como una contraseña: no lo pegues en ningún archivo, solo aquí |
| `TELEGRAM_CANAL` | `@redmarcianapods` |
| `TELEGRAM_CANAL_CHAT` | `@redmarciana`. **Opcional**: si lo dejas vacío, el bot ni lo intenta |

### 4. Probar antes de soltarlo

En la pestaña **Actions** → *Buscar podcasts nuevos* → **Run workflow**. Hay cuatro
modos en el desplegable:

| Modo | Qué hace |
|---|---|
| **prueba** | Manda un mensaje de mentira. Si llega, Telegram está bien montado |
| **seco** | Mira las webs y escribe en el registro qué publicaría, sin publicar nada |
| **estreno** | **Solo el primer día.** Publica el último episodio de cada podcast, para que el canal no nazca vacío |
| **normal** | Lo de verdad. Es también lo que hace solo cada día |

El orden recomendado el primer día: **prueba** → **seco** → **estreno**. A partir de
ahí ya se ocupa él.

Si en vez de *estreno* lanzas *normal* la primera vez, el bot apunta por dónde va
cada podcast y **no avisa de nada**. Es a propósito: si no, recibirías cientos de
mensajes con episodios de hace años. El canal se quedaría vacío hasta el siguiente
programa, y por eso existe el modo *estreno*.

---

## Cambiar cosas

### Añadir o quitar podcasts

Todo está en **`podcasts.py`**, que es el único archivo pensado para que lo toques.
Ahora mismo vigila **El Aftershow**, **Marcianos en un Tren** y **Jugones**. Al final
del archivo están *Ficción Marciana* y *Área 51*, apagados a propósito y listos para
volver con quitarles las almohadillas.

### El emoji de cada podcast

También en `podcasts.py`. Cada uno tiene el suyo y sale a la derecha del nombre:

```
🎙️ El Aftershow 📺
🎙️ Marcianos en un Tren 🚂
🎙️ Jugones 👾
```

Cambiarlo es pegar otro emoji en su línea. Si dejas `""`, sale solo el micrófono.
El micrófono es igual para todos y está en `telegram.py`, en `EMOJI_DE_TODOS`.

### Cada cuánto mira

En `check.yml`: `- cron: '15 10,11,22,23 * * *'`.

Los horarios de GitHub van en **hora UTC y no cambian con el horario de verano**.
España es UTC+2 en verano y UTC+1 en invierno, así que cada hora que queremos
aparece dos veces, una para cada mitad del año:

- **22:15 y 23:15 UTC** → las 00:15 de España. Marcianos sale los jueves a las 00:03,
  y el Aftershow suele salir a esa misma hora.
- **10:15 y 11:15 UTC** → las 12:15 de España, porque el Aftershow a veces sale a
  mediodía.

La ejecución que no toca se lanza una hora antes o después, mira y se calla. Son
cuatro al día, unas 120 al mes.

---

## Qué archivo hace qué

| Archivo | Para qué sirve |
|---|---|
| `podcasts.py` | **La lista de podcasts.** Lo único que vas a querer tocar |
| `ivoox.py` | Lee la web de iVoox y saca título, portada, descripción y duración |
| `telegram.py` | Monta el mensaje bonito y lo publica (y lo ancla, si toca) |
| `main.py` | Decide qué es nuevo y qué no |
| `pruebas.py` | Comprueba que nada se ha roto. **Ejecútalo siempre antes de subir** |
| `estado.json` | La memoria: por dónde va cada podcast |

Las pruebas se ejecutan también solas dentro del propio GitHub Actions, antes de
publicar nada. Si algo estuviera roto, se para ahí y no manda mensajes raros.

## Cómo sabe qué es nuevo

Cada episodio de iVoox tiene un número en su dirección (`..._rf_179260903_1.html`)
y ese número **siempre va a más**. El bot guarda en `estado.json` el número del
último episodio del que avisó, y todo lo que tenga un número mayor es nuevo.

Ni fechas ni RSS ni nada que se pueda congelar. Y `estado.json` no crece nunca:
son tres números.

## Si algo va mal

- **No llega nada**: mira el registro en la pestaña *Actions*. Ahí está escrito en
  castellano lo que ha pasado.
- **"chat not found"**: el bot no está metido como administrador en el canal, o el
  nombre del canal está mal escrito en los secretos.
- **"not enough rights"**: le falta permiso para publicar o para anclar.
- **"no he encontrado ni un episodio"**: iVoox ha cambiado su web. Habrá que tocar
  `ivoox.py`.
