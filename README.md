# Knowly — Chatea con tus clases universitarias

Sistema RAG que permite hacer preguntas en lenguaje natural sobre clases universitarias de YouTube, con referencias al minuto exacto del video.

## Stack

- **Backend:** FastAPI, ChromaDB, OpenAI (embeddings), Anthropic Claude (LLM), Whisper (transcripcion)
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Ingesta:** yt-dlp (audio) + Whisper (transcripcion) + OpenAI embeddings + ChromaDB

## Quickstart con Docker

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 2. Levantar todo
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Docs API: http://localhost:8000/docs

## Setup local (desarrollo)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir http://localhost:3000

## Configurar .env

```bash
cp .env.example .env
```

Editar `.env` con tus API keys:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## API Endpoints

### Clases
- `GET /classes` — lista todas las clases indexadas
- `DELETE /classes/{class_id}` — elimina una clase y sus chunks

### Ingesta
- `POST /ingest` — inicia pipeline de ingesta `{ url, title, class_id }` → `{ job_id }`
- `GET /ingest/{job_id}` — estado del job: pending, downloading, transcribing, embedding, done, error

### Chat
- `POST /chat` — pregunta con RAG `{ query, class_id? }` → `{ answer, sources }`
- `POST /chat/stream` — igual pero con streaming SSE

## CLI (legacy)

El CLI original sigue funcionando:

```bash
# Indexar
python ingest.py --url "https://www.youtube.com/watch?v=..." --title "Clase" --class_id "clase_01"

# Chatear
python chat.py
```

## Estructura del proyecto

```
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (pydantic-settings)
│   ├── schemas.py           # Pydantic models
│   ├── routers/
│   │   ├── classes.py       # CRUD clases
│   │   ├── ingest.py        # Pipeline de ingesta
│   │   └── chat.py          # Chat + streaming
│   └── services/
│       ├── ingest_service.py  # Logica de ingesta
│       └── rag_service.py     # RAG + Claude
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router
│       ├── components/      # React components
│       └── lib/api.ts       # API client
├── docker-compose.yml
├── ingest.py                # CLI original
├── rag.py                   # RAG original
└── chat.py                  # Chat CLI original
```
