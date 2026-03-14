"""RAG service: query embedding, ChromaDB search, Claude response."""

import json
from collections.abc import Generator

import anthropic
import chromadb
import openai

from config import settings
from schemas import Source

SYSTEM_PROMPT_TEMPLATE = (
    "Sos Knowly, un asistente inteligente que responde preguntas sobre clases universitarias.\n"
    "Tenés acceso a fragmentos de transcripciones de clases con sus timestamps.\n\n"
    "Fragmentos relevantes:\n{context}\n\n"
    "Instrucciones:\n"
    "- Respondé usando SOLO la información de los fragmentos\n"
    "- Siempre indicá en qué clase y en qué minuto se encuentra la información\n"
    "- Incluí el link directo al minuto correspondiente\n"
    "- Si la información no está en los fragmentos, decilo claramente\n"
    "- Sé conciso y directo"
)


def _get_query_embedding(query: str) -> list[float]:
    """Generate embedding for the query using OpenAI."""
    oai = openai.OpenAI(api_key=settings.openai_api_key)
    response = oai.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    return response.data[0].embedding


def _search_chromadb(
    query_embedding: list[float], class_id: str | None = None, n_results: int = 4
) -> dict:
    """Search ChromaDB for relevant chunks."""
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    if collection.count() == 0:
        return {"documents": [[]], "metadatas": [[]]}

    query_params: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if class_id is not None:
        query_params["where"] = {"class_id": class_id}

    return collection.query(**query_params)


def _build_context_and_sources(results: dict) -> tuple[str, list[Source]]:
    """Build the context string and sources list from ChromaDB results."""
    fragments: list[str] = []
    sources: list[Source] = []

    if not results["documents"][0]:
        return "", []

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
        sources.append(
            Source(
                class_title=meta["class_title"],
                start_time=meta["start_time"],
                end_time=meta["end_time"],
                timestamp_link=meta["timestamp_link"],
                text=doc,
            )
        )

    context = "\n---\n".join(fragments)
    return context, sources


def query_rag(query: str, class_id: str | None = None) -> tuple[str, list[Source]]:
    """Answer a question using RAG. Returns (answer_text, sources)."""
    query_embedding = _get_query_embedding(query)
    results = _search_chromadb(query_embedding, class_id=class_id)
    context, sources = _build_context_and_sources(results)

    if not context:
        return (
            "No hay clases indexadas. Primero ingresá una clase usando el endpoint /ingest.",
            [],
        )

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    )

    return message.content[0].text, sources


def query_rag_stream(
    query: str, class_id: str | None = None
) -> Generator[str, None, None]:
    """Stream an answer using RAG. Yields SSE-formatted chunks."""
    query_embedding = _get_query_embedding(query)
    results = _search_chromadb(query_embedding, class_id=class_id)
    context, sources = _build_context_and_sources(results)

    if not context:
        yield "data: No hay clases indexadas. Primero ingresá una clase usando el endpoint /ingest.\n\n"
        sources_json = json.dumps([], ensure_ascii=False)
        yield f"data: [SOURCES]{sources_json}\n\n"
        return

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    with claude.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {text}\n\n"

    # Send sources at the end
    sources_dicts = [s.model_dump() for s in sources]
    sources_json = json.dumps(sources_dicts, ensure_ascii=False)
    yield f"data: [SOURCES]{sources_json}\n\n"
