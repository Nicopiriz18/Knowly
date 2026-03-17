"""RAG: query -> embedding -> Pinecone search -> prompt -> Claude -> answer."""

import os

import openai
import anthropic
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()


def answer(query: str) -> str:
    """Answer a question using RAG over indexed classes."""
    # Generate query embedding
    oai = openai.OpenAI()
    response = oai.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_embedding = response.data[0].embedding

    # Search Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME", "classes"))

    results = index.query(
        vector=query_embedding,
        top_k=4,
        include_metadata=True,
    )

    if not results.matches:
        return "No hay clases indexadas. Corre primero: python ingest.py --url '...' --title '...' --class_id '...'"

    # Build context from results
    fragments = []
    for match in results.matches:
        meta = match.metadata
        text = meta.get("text", "")
        start_min = meta["start_time"] // 60
        start_sec = meta["start_time"] % 60
        end_min = meta["end_time"] // 60
        end_sec = meta["end_time"] % 60
        fragments.append(
            f"[{meta['class_title']}] "
            f"({start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d})\n"
            f"Link: {meta['timestamp_link']}\n"
            f"{text}\n"
        )

    context = "\n---\n".join(fragments)

    system_prompt = (
        "Sos Knowly, un asistente inteligente que responde preguntas sobre clases universitarias.\n"
        "Tenes acceso a fragmentos de transcripciones de clases con sus timestamps.\n\n"
        f"Fragmentos relevantes:\n{context}\n\n"
        "Instrucciones:\n"
        "- Responde usando SOLO la informacion de los fragmentos\n"
        "- Siempre indica en que clase y en que minuto se encuentra la informacion\n"
        "- Inclui el link directo al minuto correspondiente\n"
        "- Si la informacion no esta en los fragmentos, decilo claramente\n"
        "- Se conciso y directo"
    )

    # Call Claude
    claude = anthropic.Anthropic()
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    )

    return message.content[0].text
