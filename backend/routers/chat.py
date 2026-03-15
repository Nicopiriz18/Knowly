"""Routes for chatting with indexed classes."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas import ChatRequest, ChatResponse
from services.rag_service import query_rag, query_rag_stream

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answer a question using RAG over indexed classes."""
    answer_text, sources = await query_rag(request.query, class_id=request.class_id)
    return ChatResponse(answer=answer_text, sources=sources)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream an answer using RAG with Server-Sent Events."""
    return StreamingResponse(
        query_rag_stream(request.query, class_id=request.class_id),
        media_type="text/event-stream",
    )
