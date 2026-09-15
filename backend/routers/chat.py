"""Routes for chatting with indexed classes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from config import settings
from deps import CurrentUser, get_current_user
from schemas import ChatRequest, ChatResponse
from services.class_service import get_class
from services.materia_service import get_materia
from services.rag_service import query_rag, query_rag_stream
from services.rate_limit import check_rate_limit

router = APIRouter()


def _authorize(request: ChatRequest, user: CurrentUser) -> None:
    """Rate-limit the user and make sure the requested scope belongs to them."""
    check_rate_limit(f"chat:{user.email}", settings.chat_limit_per_hour, 3600)
    if request.class_id is not None and get_class(request.class_id, user.email) is None:
        raise HTTPException(status_code=404, detail="Clase no encontrada.")
    if request.materia_id is not None and get_materia(request.materia_id, user.email) is None:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """Answer a question using RAG over the user's indexed classes."""
    _authorize(request, user)
    answer_text, sources = await query_rag(
        request.query, owner=user.email, class_id=request.class_id, materia_id=request.materia_id
    )
    return ChatResponse(answer=answer_text, sources=sources)


@router.post("/stream")
async def chat_stream(request: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """Stream an answer using RAG with Server-Sent Events."""
    _authorize(request, user)
    return StreamingResponse(
        query_rag_stream(
            request.query, owner=user.email, class_id=request.class_id, materia_id=request.materia_id
        ),
        media_type="text/event-stream",
    )
