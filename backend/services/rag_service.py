"""RAG service: LangGraph agent that orchestrates retrieval, grading, and generation."""

import json
from collections.abc import AsyncGenerator
from typing import TypedDict

import chromadb
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from config import settings
from schemas import Source

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

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

GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Sos un evaluador de relevancia. Dado un fragmento de transcripción y una pregunta, "
     "respondé SOLO con 'si' o 'no' indicando si el fragmento contiene información relevante "
     "para responder la pregunta."),
    ("human", "Fragmento:\n{document}\n\nPregunta: {query}\n\n¿Es relevante? (si/no)"),
])

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class RAGState(TypedDict):
    query: str
    class_id: str | None
    documents: list[Document]
    answer: str
    sources: list[Source]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_chromadb(query: str, class_id: str | None = None, n_results: int = 4) -> list[Document]:
    """Search ChromaDB and return LangChain Documents."""
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
    )
    query_embedding = embeddings.embed_query(query)

    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    if collection.count() == 0:
        return []

    query_params: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if class_id is not None:
        query_params["where"] = {"class_id": class_id}

    results = collection.query(**query_params)

    docs: list[Document] = []
    if results["documents"] and results["documents"][0]:
        for i, doc_text in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            docs.append(Document(page_content=doc_text, metadata=meta))
    return docs


def _docs_to_sources(docs: list[Document]) -> list[Source]:
    """Convert LangChain Documents to Source schema objects."""
    return [
        Source(
            class_title=doc.metadata["class_title"],
            start_time=doc.metadata["start_time"],
            end_time=doc.metadata["end_time"],
            timestamp_link=doc.metadata["timestamp_link"],
            text=doc.page_content,
        )
        for doc in docs
    ]


def _build_context(docs: list[Document]) -> str:
    """Build formatted context string from documents."""
    fragments: list[str] = []
    for doc in docs:
        meta = doc.metadata
        start_min = meta["start_time"] // 60
        start_sec = meta["start_time"] % 60
        end_min = meta["end_time"] // 60
        end_sec = meta["end_time"] % 60
        fragments.append(
            f"[{meta['class_title']}] "
            f"({start_min:02.0f}:{start_sec:02.0f} - {end_min:02.0f}:{end_sec:02.0f})\n"
            f"Link: {meta['timestamp_link']}\n"
            f"{doc.page_content}\n"
        )
    return "\n---\n".join(fragments)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def retrieve(state: RAGState) -> dict:
    """Retrieve relevant documents from ChromaDB."""
    docs = _search_chromadb(state["query"], class_id=state.get("class_id"))
    return {"documents": docs}


async def grade_documents(state: RAGState) -> dict:
    """Filter out irrelevant documents using a fast LLM call."""
    docs = state["documents"]
    if not docs:
        return {"documents": []}

    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=settings.anthropic_api_key,
        max_tokens=10,
    )

    relevant: list[Document] = []
    for doc in docs:
        result = await llm.ainvoke(
            GRADE_PROMPT.format_messages(document=doc.page_content, query=state["query"])
        )
        if "si" in result.content.lower():
            relevant.append(doc)

    return {"documents": relevant if relevant else docs}


def generate(state: RAGState) -> dict:
    """Generate answer using Claude with retrieved context."""
    docs = state["documents"]

    if not docs:
        return {
            "answer": "No hay clases indexadas. Primero ingresá una clase usando el endpoint /ingest.",
            "sources": [],
        }

    context = _build_context(docs)
    sources = _docs_to_sources(docs)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.anthropic_api_key,
        max_tokens=1024,
    )

    result = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["query"]),
    ])

    return {"answer": result.content, "sources": sources}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_rag_graph() -> StateGraph:
    """Build and compile the RAG LangGraph."""
    workflow = StateGraph(RAGState)

    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_edge("grade_documents", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Compile once at module level
rag_graph = build_rag_graph()


# ---------------------------------------------------------------------------
# Public API (maintains backward compatibility with chat router)
# ---------------------------------------------------------------------------

async def query_rag(query: str, class_id: str | None = None) -> tuple[str, list[Source]]:
    """Answer a question using the RAG graph. Returns (answer_text, sources)."""
    result = await rag_graph.ainvoke({
        "query": query,
        "class_id": class_id,
        "documents": [],
        "answer": "",
        "sources": [],
    })
    return result["answer"], result["sources"]


async def query_rag_stream(
    query: str, class_id: str | None = None
) -> AsyncGenerator[str, None]:
    """Stream an answer using retrieve+grade from the graph, then stream LLM directly."""
    # Step 1: Run retrieve + grade_documents
    docs = _search_chromadb(query, class_id=class_id)

    if not docs:
        yield "data: No hay clases indexadas. Primero ingresá una clase usando el endpoint /ingest.\n\n"
        sources_json = json.dumps([], ensure_ascii=False)
        yield f"data: [SOURCES]{sources_json}\n\n"
        return

    # Grade documents
    state: RAGState = {
        "query": query,
        "class_id": class_id,
        "documents": docs,
        "answer": "",
        "sources": [],
    }
    graded = await grade_documents(state)
    docs = graded["documents"]

    # Step 2: Build context and stream the LLM response
    context = _build_context(docs)
    sources = _docs_to_sources(docs)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=settings.anthropic_api_key,
        max_tokens=1024,
    )

    async for chunk in llm.astream([
        SystemMessage(content=system_prompt),
        HumanMessage(content=query),
    ]):
        if hasattr(chunk, "content") and chunk.content:
            yield f"data: {json.dumps(chunk.content, ensure_ascii=False)}\n\n"

    # Send sources at the end
    sources_dicts = [s.model_dump() for s in sources]
    sources_json = json.dumps(sources_dicts, ensure_ascii=False)
    yield f"data: [SOURCES]{sources_json}\n\n"
