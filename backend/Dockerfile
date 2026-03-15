FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: torch CPU-only (~200 MB instead of ~915 MB) — rarely changes
RUN pip install --no-cache-dir "setuptools==81.0.0" wheel \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Layer 2: whisper (pinned, rarely changes) — cached independently from requirements.txt
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20240930

# Layer 3: app dependencies — only this layer rebuilds when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
