# Deploy en Hetzner

Todo corre en un solo VPS con Docker Compose:

```
Internet ──► Caddy (80/443, HTTPS automático)
               ├── APP_DOMAIN ──► frontend (Next.js, :3000)
               └── API_DOMAIN ──► backend  (FastAPI, :8000) ──► ./data (SQLite, registros, transcripciones)
                                     └──► OpenAI · Anthropic · Pinecone · Resend · YouTube
```

## 1. Dominio y email

1. Comprá un dominio (Cloudflare Registrar, Namecheap, etc.).
2. En [Resend](https://resend.com) agregá el dominio y cargá los registros DNS que te pide (SPF/DKIM). Esperá a que figure como *verified*.
3. Creá una API key en Resend.

## 2. Servidor

1. En la [consola de Hetzner](https://console.hetzner.cloud) creá un servidor:
   - **Location:** Ashburn (US East), la más cercana a Sudamérica.
   - **Image:** Ubuntu 24.04.
   - **Type:** CPX11 (2 vCPU / 2 GB) alcanza; CPX21 si procesás muchos videos.
   - **SSH key:** subí tu clave pública (`~/.ssh/id_ed25519.pub`). Sin clave no crees el servidor.
2. Anotá la IP pública.
3. En el DNS del dominio creá dos registros **A** apuntando a esa IP:
   - `knowly.tudominio.com`
   - `api.knowly.tudominio.com`

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

SMTP_HOST=
RESEND_API_KEY=re_...
EMAIL_FROM=Knowly <no-reply@tudominio.com>

APP_DOMAIN=knowly.tudominio.com
API_DOMAIN=api.knowly.tudominio.com
FRONTEND_URL=https://knowly.tudominio.com
FRONTEND_ORIGINS=https://knowly.tudominio.com
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

Abrí `https://knowly.tudominio.com`. La primera vez Caddy tarda unos segundos en sacar el certificado.

## 7. Backups diarios

```bash
chmod +x deploy/backup.sh
crontab -e
# agregar:
0 4 * * * /opt/knowly/deploy/backup.sh >> /var/log/knowly-backup.log 2>&1
```

Quedan en `/opt/knowly-backups` (últimos 14). Conviene activar también los *Backups* de Hetzner (≈20% del precio del servidor).

## Actualizar

```bash
cd /opt/knowly
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker image prune -f
```

## Problemas comunes

- **Caddy no obtiene certificado:** revisá que los registros A apunten a la IP (`dig +short api.knowly.tudominio.com`) y que los puertos 80/443 estén abiertos.
- **La ingesta falla con "Sign in to confirm you're not a bot":** YouTube bloquea IPs de datacenter. Exportá cookies de tu navegador (extensión *Get cookies.txt LOCALLY*) y pasáselas a yt-dlp con `--cookies` (requiere un cambio chico en `ingest_service.py`).
- **Errores de CORS:** `FRONTEND_ORIGINS` tiene que ser exactamente `https://` + `APP_DOMAIN`, sin `/` final.
- **Cambié `API_DOMAIN`:** hay que reconstruir el frontend (`up -d --build`), porque la URL queda embebida en el bundle.
