# Knowly — Chateá con tus clases universitarias

Sistema RAG que permite hacer preguntas en lenguaje natural sobre clases de Khan Academy, con referencias al minuto exacto.

## 1. Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

## 2. Configurar .env

```bash
cp .env.example .env
```

Editá `.env` con tus API keys:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## 3. Indexar una clase

Los videos de Khan Academy están alojados en YouTube. Para indexar una clase:

1. Abrí el video en Khan Academy
2. Copiá la URL de YouTube del reproductor embebido (click derecho → "Copiar URL del video")
3. Ejecutá:

```bash
python ingest.py --url "https://www.youtube.com/watch?v=CJyxxrl2JJg" --title "Álgebra - Variables" --class_id "algebra_01"
```

> **Nota:** Los videos de Khan Academy deben ser públicos. Usá la URL de YouTube directamente ya que el extractor de Khan Academy de yt-dlp puede no estar actualizado.

Esto descarga el audio, lo transcribe con Whisper, genera chunks con timestamps, y los guarda en ChromaDB. Los links de timestamp apuntan directamente al minuto en YouTube.

## 4. Chatear

```bash
python chat.py
```

## 5. Ejemplos de preguntas

- "¿Qué es una variable según la clase?"
- "¿En qué minuto se explican las ecuaciones?"
- "Explicame el concepto de álgebra según la clase"
- "¿Cuáles fueron los ejemplos que dio el profesor?"
- "¿Qué temas se vieron en la clase de álgebra?"
