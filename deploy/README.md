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
```

`NEXT_PUBLIC_API_URL` y `FORWARDED_ALLOW_IPS` los define `docker-compose.prod.yml`; no hace falta cargarlos.

## 5. (Opcional) Subir los datos que ya tenés

Las clases ya ingeridas viven en Pinecone **y** en `data/`. Si usás la misma `PINECONE_API_KEY`, subí `data/` para que coincidan. Desde tu máquina:

```bash
scp -r data/classes_registry.json data/materias.json data/transcripts data/visual root@<IP>:/opt/knowly/data/
```

## 6. Levantar

```bash
cd /opt/knowly
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

Abrí `https://knowly.duckdns.org`. La primera vez Caddy tarda unos segundos en sacar el certificado.

## 7. Backups diarios

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

## Problemas comunes

- **Caddy no obtiene certificado:** revisá que los registros A apunten a la IP (`dig +short api.knowly.duckdns.org`) y que los puertos 80/443 estén abiertos.
- **No llegan los mails:** revisá `docker compose -f docker-compose.prod.yml logs backend`. `Network is unreachable` o un timeout significa que el puerto SMTP está bloqueado (usá el 2525); un error `535` significa que el Login o la SMTP key están mal. Mirá también la carpeta de spam.
- **La ingesta falla con "Sign in to confirm you're not a bot":** YouTube bloquea IPs de datacenter. Exportá cookies de tu navegador (extensión *Get cookies.txt LOCALLY*) y pasáselas a yt-dlp con `--cookies` (requiere un cambio chico en `ingest_service.py`).
- **Errores de CORS:** `FRONTEND_ORIGINS` tiene que ser exactamente `https://` + `APP_DOMAIN`, sin `/` final.
- **Cambié `API_DOMAIN`:** hay que reconstruir el frontend (`up -d --build`), porque la URL queda embebida en el bundle.
