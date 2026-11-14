"""Clinician chatbot: conversations (optionally tied to an analysis) with streamed answers (SSE)."""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import ChatMessage, Conversation, User
from ..ratelimit import limiter
from ..schemas import ConversationIn, ConversationOut, ConversationSummary, MessageIn
from ..security import get_current_user
from ..services.ai import AIError, AIProvider, get_ai
from .analyses import build_case, owned_analysis

router = APIRouter(prefix="/api/conversations", tags=["chat"])
log = logging.getLogger("mediai.chat")


def owned_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    c = db.scalar(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .options(selectinload(Conversation.messages))
    )
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")
    return c


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    analysis_id: uuid.UUID | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if analysis_id:
        stmt = stmt.where(Conversation.analysis_id == analysis_id)
    return db.scalars(stmt.order_by(Conversation.updated_at.desc()).limit(200)).all()


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(body: ConversationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    title = body.title or "Nouvelle discussion"
    if body.analysis_id:
        a = owned_analysis(db, user, body.analysis_id)
        if a.status != "done":
            raise HTTPException(status.HTTP_409_CONFLICT, "L'analyse doit être terminée avant d'en discuter")
        title = body.title or f"Discussion : {a.title}"[:200]
    c = Conversation(user_id=user.id, analysis_id=body.analysis_id, title=title[:200])
    db.add(c)
    db.commit()
    return ConversationOut(id=c.id, title=c.title, analysis_id=c.analysis_id,
                           created_at=c.created_at, updated_at=c.updated_at, messages=[])


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_conversation(db, user, conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(owned_conversation(db, user, conversation_id))
    db.commit()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: uuid.UUID,
    body: MessageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai),
):
    limiter.hit(f"chat:{user.id}", get_settings().chat_messages_per_hour, 3600)
    conv = owned_conversation(db, user, conversation_id)
    case = None
    if conv.analysis_id:
        case = build_case(owned_analysis(db, user, conv.analysis_id, with_content=True), include_report=True)

    first_message = not conv.messages
    user_msg = ChatMessage(role="user", content=body.content)
    conv.messages.append(user_msg)  # keeps the in-memory history in sync for the prompt below
    if first_message and conv.analysis_id is None:
        conv.title = body.content.strip().splitlines()[0][:80] or conv.title
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    conv_id = conv.id

    def events():
        chunks: list[str] = []
        yield _sse("start", {"user_message_id": str(user_msg.id)})
        try:
            for text in ai.chat_stream(case, history):
                chunks.append(text)
                yield _sse("delta", {"text": text})
        except AIError as exc:
            yield _sse("error", {"message": str(exc)})
        except Exception:  # noqa: BLE001 - stream must end cleanly for the client
            log.exception("chat stream failed")
            yield _sse("error", {"message": "Erreur interne du chatbot."})
        answer = "".join(chunks).strip()
        if answer:
            with SessionLocal() as s:  # request session is closed once streaming starts
                msg = ChatMessage(conversation_id=conv_id, role="assistant", content=answer)
                s.add(msg)
                s.commit()
                yield _sse("done", {"assistant_message_id": str(msg.id)})
        else:
            yield _sse("done", {"assistant_message_id": None})

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
