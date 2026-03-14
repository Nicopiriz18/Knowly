"""RAG: query → embedding → ChromaDB search → prompt → Claude → answer."""

import chromadb
import openai
import anthropic
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "chroma_db"


def answer(query: str) -> str:
    """Answer a question using RAG over indexed classes."""
    # Generate query embedding
    oai = openai.OpenAI()
    response = oai.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_embedding = response.data[0].embedding

    # Search ChromaDB
    chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma.get_or_create_collection("classes")

    if collection.count() == 0:
        return "No hay clases indexadas. Corré primero: python ingest.py --url 'https://www.khanacademy.org/...' --title '...' --class_id '...'"

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=4,
    )

    # Build context from results
    fragments = []
    for i in range(len(results["documents"][0])):
        doc = results["documents"][0][i]
        meta = results["metadatas"][0][i]
        start_min = meta["start_time"] // 60
        start_sec = meta["start_time"] % 60
        end_min = meta["end_time"] // 60
        end_sec = meta["end_time"] % 60
        fragments.append(
            f"[{meta['class_title']}] "
            f"({start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d})\n"
            f"Link: {meta['timestamp_link']}\n"
            f"{doc}\n"
        )

    context = "\n---\n".join(fragments)

    system_prompt = (
        "Sos Knowly, un asistente inteligente que responde preguntas sobre clases universitarias.\n"
        "Tenés acceso a fragmentos de transcripciones de clases con sus timestamps.\n\n"
        f"Fragmentos relevantes:\n{context}\n\n"
        "Instrucciones:\n"
        "- Respondé usando SOLO la información de los fragmentos\n"
        "- Siempre indicá en qué clase y en qué minuto se encuentra la información\n"
        "- Incluí el link directo al minuto correspondiente\n"
        "- Si la información no está en los fragmentos, decilo claramente\n"
        "- Sé conciso y directo"
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
