# Deploy en DigitalOcean

Todo corre en un solo VPS con Docker Compose:

```
Internet ──► Caddy (80/443, HTTPS automático)
               ├── APP_DOMAIN ──► frontend (Next.js, :3000)
               └── API_DOMAIN ──► backend  (FastAPI, :8000) ──► ./data (SQLite, registros, transcripciones)
                                     └──► OpenAI · Anthropic · Pinecone · Gmail · YouTube
```

## 1. Email (Brevo, gratis)

DigitalOcean bloquea los puertos SMTP 25, 465 y 587, así que Gmail directo no funciona desde el droplet. Los códigos de acceso salen por [Brevo](https://www.brevo.com) (300 mails por día gratis), que acepta SMTP por el puerto 2525.

1. Creá una cuenta en Brevo y verificá el teléfono.
2. En *Senders, domains, IPs → Senders*, verificá la dirección remitente (por ejemplo `knowly.app@gmail.com`).
3. En *SMTP & API → SMTP*, copiá el **Login** y generá una **SMTP key**.

> Si más adelante comprás un dominio, podés pasarte a Resend: dejá `SMTP_HOST` vacío y cargá `RESEND_API_KEY`.

## 2. Servidor

1. En [DigitalOcean](https://cloud.digitalocean.com) creá un droplet (*Create → Droplets*):
   - **Region:** New York, la más cercana a Sudamérica.
   - **Image:** Ubuntu 24.04 (LTS).
   - **Size:** Basic, 2 GB / 1 vCPU alcanza; 4 GB si procesás muchos videos.
   - **Authentication:** SSH Key, y pegá tu clave pública (`~/.ssh/id_ed25519.pub`). No uses contraseña.
2. Anotá la IP pública.
3. Dominio gratis con [DuckDNS](https://www.duckdns.org): entrá con GitHub o Google, creá un subdominio (por ejemplo `knowly`) y en *current ip* poné la IP del servidor.
   - La app queda en `knowly.duckdns.org`.
   - La API en `api.knowly.duckdns.org`: DuckDNS resuelve cualquier sub-subdominio a la misma IP, no hay que configurar nada más.

## 3. Preparar el servidor

```bash
ssh root@<IP>
git clone https://github.com/Nicopiriz18/Knowly.git /opt/knowly
cd /opt/knowly
bash deploy/setup-server.sh
```

> Si el repo es privado, usá un [fine-grained token](https://github.com/settings/tokens) de solo lectura como contraseña al clonar.

## 4. Variables de entorno

```bash
cp .env.example .env
nano .env
```

Valores de producción:

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
PINECONE_API_KEY=...
JWT_SECRET=<python3 -c "import secrets; print(secrets.token_urlsafe(48))">
ADMIN_EMAILS=tu@mail.com

SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=2525
SMTP_USERNAME=<Login de Brevo, termina en @smtp-brevo.com>
SMTP_PASSWORD=<SMTP key de Brevo>
EMAIL_FROM=Knowly <knowly.app@gmail.com>
RESEND_API_KEY=

APP_DOMAIN=knowly.duckdns.org
API_DOMAIN=api.knowly.duckdns.org
FRONTEND_URL=https://knowly.duckdns.org
FRONTEND_ORIGINS=https://knowly.duckdns.org

YTDLP_COOKIES_FILE=/app/data/youtube_cookies.txt
```

`NEXT_PUBLIC_API_URL` y `FORWARDED_ALLOW_IPS` los define `docker-compose.prod.yml`; no hace falta cargarlos.

## 5. (Opcional) Subir los datos que ya tenés

Las clases ya ingeridas viven en Pinecone **y** en `data/`. Si usás la misma `PINECONE_API_KEY`, subí `data/` para que coincidan. Desde tu máquina:

```bash
scp -r data/classes_registry.json data/materias.json data/transcripts data/visual root@<IP>:/opt/knowly/data/
```

## 6. Cookies de YouTube

YouTube bloquea las IPs de datacenter ("Sign in to confirm you're not a bot"), así que yt-dlp descarga con las cookies de una cuenta logueada. El backend las lee del archivo que indica `YTDLP_COOKIES_FILE` (en producción, `/app/data/youtube_cookies.txt`, que en el servidor es `/opt/knowly/data/youtube_cookies.txt`). En local no hace falta: dejá la variable vacía.

### Exportar

1. Usá una **cuenta de Google descartable**, no la personal: YouTube puede restringir cuentas con uso automatizado.
2. Instalá la extensión [Get cookies.txt LOCALLY](https://chromewebstore.google.com/search/get%20cookies.txt%20locally) y, en `chrome://extensions` → *Detalles*, activá **Permitir en modo incógnito**.
3. Abrí una ventana de incógnito, entrá a <https://www.youtube.com> e iniciá sesión. **Confirmá que arriba a la derecha aparece el avatar de la cuenta** y no el botón "Acceder"; si no, recargá. Reproducí un video unos segundos.
4. En esa misma pestaña de YouTube: extensión → **Export** (formato Netscape). Guardá el archivo como `youtube_cookies.txt`.
5. Cerrá la ventana de incógnito **sin cerrar sesión**: si cerrás sesión o seguís usando esa ventana, Google invalida o rota las cookies exportadas.

### Verificar antes de subir

El archivo tiene que incluir las cookies de sesión (`SID`, `SAPISID`, `__Secure-3PSID`, `LOGIN_INFO`...). Si solo trae cookies de visitante (`VISITOR_INFO1_LIVE`, `YSC`, `PREF`), se exportó sin la sesión iniciada y YouTube va a seguir bloqueando. En PowerShell, desde la carpeta del archivo:

```powershell
Select-String -Path youtube_cookies.txt -Pattern "LOGIN_INFO" -SimpleMatch -Quiet
```

Tiene que devolver `True`. Si devuelve `False`, repetí la exportación.

### Subir y probar

```bash
scp youtube_cookies.txt root@<IP>:/opt/knowly/data/youtube_cookies.txt
ssh root@<IP> chmod 600 /opt/knowly/data/youtube_cookies.txt
```

No hace falta reiniciar: el archivo se lee en cada ingesta. Para comprobarlo sin crear una clase, en el servidor:

```bash
cd /opt/knowly
docker compose -f docker-compose.prod.yml exec -T backend python -c \
  "from services.ingest_service import _run_ytdlp; import json; print(json.loads(_run_ytdlp('--dump-json', '--no-download', '--', 'https://youtu.be/<VIDEO_ID>'))['title'])"
```

Si imprime el título del video, funciona. Después **borrá la copia local** del archivo: contiene la sesión de la cuenta.

### Renovar

Las cookies vencen sin aviso: típicamente en semanas o un par de meses, antes si se usan mucho o si se cierra sesión en esa cuenta. Cuando vencen, la ingesta falla con *"YouTube bloqueó la descarga desde el servidor… Hay que cargar o renovar las cookies de YouTube"*. Repetí **Exportar**, **Verificar** y **Subir** con la misma cuenta; el archivo nuevo reemplaza al anterior.

Notas:

- yt-dlp reescribe el archivo con las cookies que le devuelve YouTube, lo que ayuda a que la sesión dure más. Por eso tiene que ser escribible dentro del contenedor (lo es, porque `data/` está montado).
- `.gitignore` excluye `data/*cookies*.txt`: el archivo nunca debe entrar al repo. Los backups de `deploy/backup.sh` sí lo incluyen y quedan en `/opt/knowly-backups`, accesible solo por root.
- Si las cookies empiezan a vencer muy seguido, la alternativa es un proxy residencial pago (yt-dlp `--proxy`).

## 7. Levantar

```bash
cd /opt/knowly
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

Abrí `https://knowly.duckdns.org`. La primera vez Caddy tarda unos segundos en sacar el certificado.

## 8. Backups diarios

```bash
chmod +x deploy/backup.sh
crontab -e
# agregar:
0 4 * * * /opt/knowly/deploy/backup.sh >> /var/log/knowly-backup.log 2>&1
```

Quedan en `/opt/knowly-backups` (últimos 14). Conviene activar también los *Backups* de DigitalOcean (desde ≈20% del precio del droplet).

## Actualizar

```bash
cd /opt/knowly
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker image prune -f
```

Si el cambio toca `deploy/Caddyfile`, recreá Caddy: el archivo está montado suelto y `git pull` lo reemplaza, así que un `caddy reload` seguiría leyendo la versión anterior.

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps caddy
```

## Problemas comunes

- **Caddy no obtiene certificado:** revisá que los registros A apunten a la IP (`dig +short api.knowly.duckdns.org`) y que los puertos 80/443 estén abiertos.
- **No llegan los mails:** revisá `docker compose -f docker-compose.prod.yml logs backend`. `Network is unreachable` o un timeout significa que el puerto SMTP está bloqueado (usá el 2525); un error `535` significa que el Login o la SMTP key están mal. Mirá también la carpeta de spam.
- **La ingesta dice que YouTube bloqueó la descarga:** las cookies vencieron o se exportaron sin la sesión iniciada. Seguí [Renovar](#renovar) en el paso 6.
- **La ingesta dice "No se encontró el archivo de cookies":** `YTDLP_COOKIES_FILE` apunta a un archivo que no existe; subilo (paso 6) o revisá la ruta en `.env`.
- **Errores de CORS:** `FRONTEND_ORIGINS` tiene que ser exactamente `https://` + `APP_DOMAIN`, sin `/` final.
- **Cambié `API_DOMAIN`:** hay que reconstruir el frontend (`up -d --build`), porque la URL queda embebida en el bundle.
