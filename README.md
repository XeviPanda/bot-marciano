# Bot Marciano

Avisa en Telegram cuando Red Marciana publica un podcast nuevo.

Sustituye al viejo `@ivooxrssbot`. Lee **dos sitios y usa el que funcione**: primero
el RSS del podcast, y si el RSS falla, la página web. No es paranoia, es que los dos
se han roto ya, cada uno por su lado:

- **Mayo 2026** — los RSS de El Aftershow y Marcianos se congelaron: servían siempre
  los mismos 100 episodios aunque la web estuviera al día. Por eso el bot nació
  leyendo la web.
- **Noviembre 2026** — iVoox empezó a devolver *502 Bad Gateway* a las peticiones que
  salen de los servidores de GitHub, y el bot se calló tres días. Desde casa la web
  se veía perfectamente. A la vez, iVoox arregló los RSS, que ahora traen el catálogo
  completo. Así que ahora el RSS es el camino principal y la web, el plan B.

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

En `check.yml`: `- cron: '17 */2 * * *'`. Una pasada **cada dos horas**, doce al día.

Esto empezó siendo un horario fino (a las 00:07, justo después de que salgan los
episodios) y acabó siendo esto. La razón es que **la hora que le pides a GitHub no
es la hora a la que se ejecuta**: no te da una cita, te mete en una cola y te
atiende cuando tiene hueco. Medido en este repositorio, los retrasos iban de hora y
media a más de cuatro horas, y de las diez horas que pedíamos solo lanzaba cinco.

Con una pasada cada dos horas eso deja de importar: llegue GitHub cuando llegue, el
episodio nunca espera mucho. Y desaparece de paso el lío del horario de verano
(España es UTC+2 en verano y UTC+1 en invierno, y los cron de GitHub van en UTC sin
enterarse del cambio), porque una hora arriba o abajo da igual.

El minuto 17 tampoco es capricho: en los minutos redondos es cuando todo el mundo
ha programado lo suyo y la cola se dispara.

Si algún día quieres más cobertura, `'17 * * * *'` es cada hora. En un repositorio
público los minutos de Actions son gratis e ilimitados.

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

En `estado.json` guarda la **lista** de episodios de los que ya ha avisado, por su
número (el que sale en la dirección: `..._rf_182949557_1.html`). Lo que no esté en
esa lista y se haya publicado en los últimos diez días, se avisa.

Antes guardaba solo el número más alto, dando por hecho que los números van siempre
a más. **No es verdad, y nos costó un episodio:**

```
MAR 536  salió el  8 oct  con el número 181850904
MAR 537  salió el 15 oct  con el número 181699760   ← más bajo
```

iVoox pone el número cuando **subes** el episodio, no cuando se publica. Como los
dejas programados con antelación, uno grabado antes puede salir después y llevar un
número menor. Con la regla vieja, el MAR 537 se dio por visto sin haberse publicado
nunca, y nadie se enteró. Por eso ahora se guarda la lista entera.

Lo de los diez días es la red de seguridad: si iVoox reordena su catálogo o resucita
algo antiguo, que no te llegue de madrugada un aviso de un programa de hace dos años.
La lista se queda en los últimos 400 episodios, así que el archivo no crece: un kilobyte.

## Si algo va mal

- **No llega nada**: mira el registro en la pestaña *Actions*. Ahí está escrito en
  castellano lo que ha pasado.
- **"chat not found"**: el bot no está metido como administrador en el canal, o el
  nombre del canal está mal escrito en los secretos.
- **"not enough rights"**: le falta permiso para publicar o para anclar.
- **"no he encontrado ni un episodio"**: iVoox ha cambiado su web. Habrá que tocar
  `ivoox.py`.
