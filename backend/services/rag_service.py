"""RAG service: LangGraph agent that orchestrates retrieval, grading, and generation."""

import json
from collections.abc import AsyncGenerator
from typing import TypedDict
from uuid import uuid4

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from config import settings
from schemas import Source
from services.pinecone_client import get_index
from services.class_service import class_titles, list_classes
from services import observability


def _observability_config(owner: str) -> RunnableConfig:
    """LangChain config that traces one chat turn (classifier, grading, answer) in PostHog.

    Prompts and answers are captured; the user is identified by a hash of the email.
    """
    if not observability.enabled:
        return {}
    from posthog.ai.langchain import CallbackHandler

    handler = CallbackHandler(
        client=observability.posthog_client,
        distinct_id=observability.distinct_id(owner),
        trace_id=str(uuid4()),
    )
    return {"callbacks": [handler]}


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = (
    "Sos Knowly, un asistente inteligente que responde preguntas sobre clases universitarias.\n"
    "Tenés acceso a fragmentos de transcripciones de clases con sus timestamps.\n"
    "Algunos fragmentos incluyen descripciones del contenido visual mostrado en pantalla (slides, formulas, codigo, diagramas).\n\n"
    "Fragmentos relevantes:\n{context}\n\n"
    "Instrucciones:\n"
    "- Respondé usando SOLO la información de los fragmentos\n"
    "- Siempre indicá en qué clase y en qué minuto se encuentra la información\n"
    "- Incluí el link directo al minuto correspondiente\n"
    "- Si la información no está en los fragmentos, decilo claramente\n"
    "- Sé conciso y directo"
)

BROAD_INSTRUCTION = (
    "\n- Organizá la respuesta por clase, dando un resumen de los temas principales de cada una"
)

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Clasificá la siguiente pregunta del usuario como 'broad' o 'specific'.\n\n"
     "broad = preguntas que piden resúmenes, overviews, o información de múltiples clases. "
     "Ejemplos: 'qué se dio en cada clase', 'haceme un resumen de la materia', "
     "'cuáles fueron los temas principales'.\n\n"
     "specific = preguntas puntuales sobre un tema concreto. "
     "Ejemplos: 'qué es un árbol binario', 'cómo funciona quicksort', "
     "'qué dijo el profesor sobre herencia'.\n\n"
     "Respondé SOLO con 'broad' o 'specific'."),
    ("human", "{query}"),
])

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
    owner: str
    class_id: str | None
    materia_id: str | None
    documents: list[Document]
    answer: str
    sources: list[Source]
    query_type: str  # "broad" or "specific"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_pinecone(
    query: str,
    owner: str,
    class_id: str | None = None,
    materia_id: str | None = None,
    n_results: int = 4,
    per_class_results: int = 2,
) -> list[Document]:
    """Search Pinecone and return LangChain Documents.

    When searching by materia_id, retrieves top chunks from each class
    separately to ensure coverage across all classes in the materia.
    Callers must verify that class_id / materia_id belong to `owner`;
    unscoped searches are restricted to the owner's classes.
    """
    owned_class_ids = [c["class_id"] for c in list_classes(owner)]
    if not owned_class_ids:
        return []

    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
    )
    query_embedding = embeddings.embed_query(query)

    index = get_index()

    # When querying by materia, search per-class to ensure diversity
    if materia_id is not None and class_id is None:
        return _search_per_class(
            index, query_embedding, owner, materia_id, per_class_results
        )

    query_params: dict = {
        "vector": query_embedding,
        "top_k": n_results,
        "include_metadata": True,
    }
    if class_id is not None:
        query_params["filter"] = {"class_id": {"$eq": class_id}}
    else:
        query_params["filter"] = {"class_id": {"$in": owned_class_ids}}

    results = index.query(**query_params)

    docs: list[Document] = []
    for match in results.matches:
        meta = dict(match.metadata)
        text = meta.pop("text", "")
        docs.append(Document(page_content=text, metadata=meta))
    return docs


def _search_per_class(
    index,
    query_embedding: list[float],
    owner: str,
    materia_id: str,
    per_class: int = 2,
) -> list[Document]:
    """Retrieve top chunks from each class in a materia for broad coverage."""
    # Discover class_ids from the JSON registry
    classes = list_classes(owner, materia_id)
    class_ids = [c["class_id"] for c in classes]

    if not class_ids:
        return []

    # Query each class separately and collect results
    docs: list[Document] = []
    for cid in class_ids:
        results = index.query(
            vector=query_embedding,
            top_k=per_class,
            filter={"class_id": {"$eq": cid}},
            include_metadata=True,
        )
        for match in results.matches:
            meta = dict(match.metadata)
            text = meta.pop("text", "")
            docs.append(Document(page_content=text, metadata=meta))

    return docs


def _cap_context(docs: list[Document], max_chars: int | None = None) -> list[Document]:
    """If total character count exceeds max_chars, trim docs proportionally per class."""
    max_chars = max_chars or settings.max_context_chars
    total = sum(len(d.page_content) for d in docs)
    if total <= max_chars:
        return docs

    # Group by class_id
    by_class: dict[str, list[Document]] = {}
    for doc in docs:
        cid = doc.metadata.get("class_id", "unknown")
        by_class.setdefault(cid, []).append(doc)

    # Reduce proportionally: keep ratio of max_chars/total docs per class
    ratio = max_chars / total
    capped: list[Document] = []
    for cid, class_docs in by_class.items():
        keep = max(1, int(len(class_docs) * ratio))
        capped.extend(class_docs[:keep])

    return capped


def _apply_current_titles(docs: list[Document]) -> list[Document]:
    """Replace the title stored in each chunk with the class's current one (it may have been renamed)."""
    titles = class_titles()
    for doc in docs:
        doc.metadata["class_title"] = titles.get(doc.metadata.get("class_id"), doc.metadata["class_title"])
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


async def classify_query(query: str, config: RunnableConfig | None = None) -> str:
    """Classify a query as 'broad' or 'specific' using a fast LLM call."""
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=settings.anthropic_api_key,
        max_tokens=10,
    )
    result = await llm.ainvoke(
        CLASSIFY_PROMPT.format_messages(query=query), config=config
    )
    classification = result.content.strip().lower()
    return "broad" if "broad" in classification else "specific"


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

async def classify(state: RAGState, config: RunnableConfig) -> dict:
    """Classify the query as broad or specific."""
    query_type = await classify_query(state["query"], config)
    return {"query_type": query_type}


def retrieve(state: RAGState) -> dict:
    """Retrieve relevant documents from Pinecone, adapting to query type."""
    query_type = state.get("query_type", "specific")

    if query_type == "broad":
        per_class = settings.broad_per_class_results
        n_results = settings.broad_n_results
    else:
        per_class = 2
        n_results = 4

    docs = _search_pinecone(
        state["query"],
        owner=state["owner"],
        class_id=state.get("class_id"),
        materia_id=state.get("materia_id"),
        n_results=n_results,
        per_class_results=per_class,
    )

    if query_type == "broad":
        docs = _cap_context(docs)

    return {"documents": docs}


async def grade_documents(state: RAGState, config: RunnableConfig | None = None) -> dict:
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
            GRADE_PROMPT.format_messages(document=doc.page_content, query=state["query"]),
            config=config,
        )
        if "si" in result.content.lower():
            relevant.append(doc)

    return {"documents": relevant if relevant else docs}


def generate(state: RAGState, config: RunnableConfig) -> dict:
    """Generate answer using Claude with retrieved context."""
    docs = state["documents"]
    query_type = state.get("query_type", "specific")

    if not docs:
        return {
            "answer": "No hay clases indexadas. Primero ingresá una clase usando el endpoint /ingest.",
            "sources": [],
        }

    docs = _apply_current_titles(docs)
    context = _build_context(docs)
    sources = _docs_to_sources(docs)

    prompt_template = SYSTEM_PROMPT_TEMPLATE
    if query_type == "broad":
        prompt_template += BROAD_INSTRUCTION

    system_prompt = prompt_template.format(context=context)
    max_tokens = settings.broad_max_tokens if query_type == "broad" else 8000
    llm = _answer_llm(max_tokens)

    result = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["query"]),
        ],
        config=config,
    )

    # .text: with thinking on, .content is a list of blocks rather than a string
    return {"answer": str(result.text), "sources": sources}


def _answer_llm(max_tokens: int) -> ChatAnthropic:
    """Model that writes the final answer.

    Opus 5.5 can't disable thinking; low effort keeps answers about as fast as before.
    Thinking tokens count toward max_tokens. "fallbacks" reroutes requests that the
    safety classifiers decline to another model instead of failing.
    """
    return ChatAnthropic(
        model="claude-opus-5-5",
        api_key=settings.anthropic_api_key,
        max_tokens=max_tokens,
        effort="low",
        betas=["server-side-fallback-2026-07-01"],
        model_kwargs={"fallbacks": "default"},
    )


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _route_after_retrieve(state: RAGState) -> str:
    """Route: skip grading for broad queries."""
    if state.get("query_type") == "broad":
        return "generate"
    return "grade_documents"


def build_rag_graph() -> StateGraph:
    """Build and compile the RAG LangGraph."""
    workflow = StateGraph(RAGState)

    workflow.add_node("classify", classify)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)

    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "retrieve")
    workflow.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {"grade_documents": "grade_documents", "generate": "generate"},
    )
    workflow.add_edge("grade_documents", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Compile once at module level
rag_graph = build_rag_graph()


# ---------------------------------------------------------------------------
# Public API (maintains backward compatibility with chat router)
# ---------------------------------------------------------------------------

async def query_rag(
    query: str,
    owner: str,
    class_id: str | None = None,
    materia_id: str | None = None,
) -> tuple[str, list[Source]]:
    """Answer a question using the RAG graph. Returns (answer_text, sources)."""
    result = await rag_graph.ainvoke(
        {
            "query": query,
            "owner": owner,
            "class_id": class_id,
            "materia_id": materia_id,
            "documents": [],
            "answer": "",
            "sources": [],
            "query_type": "",
        },
        config=_observability_config(owner),
    )
    return result["answer"], result["sources"]


async def query_rag_stream(
    query: str,
    owner: str,
    class_id: str | None = None,
    materia_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream an answer using retrieve+grade from the graph, then stream LLM directly."""
    observability_config = _observability_config(owner)

    # Step 1: Classify query
    query_type = await classify_query(query, observability_config)

    # Step 2: Retrieve with adaptive parameters
    if query_type == "broad":
        per_class = settings.broad_per_class_results
        n_results = settings.broad_n_results
    else:
        per_class = 2
        n_results = 4

    docs = _search_pinecone(
        query, owner=owner, class_id=class_id, materia_id=materia_id,
        n_results=n_results, per_class_results=per_class,
    )

    if not docs:
        yield "data: No hay clases indexadas. Primero ingresá una clase usando el endpoint /ingest.\n\n"
        sources_json = json.dumps([], ensure_ascii=False)
        yield f"data: [SOURCES]{sources_json}\n\n"
        return

    # Step 3: Cap context for broad queries
    if query_type == "broad":
        docs = _cap_context(docs)
    else:
        # Grade documents only for specific queries
        state: RAGState = {
            "query": query,
            "owner": owner,
            "class_id": class_id,
            "materia_id": materia_id,
            "documents": docs,
            "answer": "",
            "sources": [],
            "query_type": query_type,
        }
        graded = await grade_documents(state, observability_config)
        docs = graded["documents"]

    # Step 4: Build context and stream the LLM response
    docs = _apply_current_titles(docs)
    context = _build_context(docs)
    sources = _docs_to_sources(docs)

    prompt_template = SYSTEM_PROMPT_TEMPLATE
    if query_type == "broad":
        prompt_template += BROAD_INSTRUCTION

    system_prompt = prompt_template.format(context=context)
    max_tokens = settings.broad_max_tokens if query_type == "broad" else 8000
    llm = _answer_llm(max_tokens)

    async for chunk in llm.astream(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ],
        config=observability_config,
    ):
        if chunk.text:
            yield f"data: {json.dumps(chunk.text, ensure_ascii=False)}\n\n"

    # Send sources at the end
    sources_dicts = [s.model_dump() for s in sources]
    sources_json = json.dumps(sources_dicts, ensure_ascii=False)
    yield f"data: [SOURCES]{sources_json}\n\n"
