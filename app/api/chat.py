from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.diagnosis import Diagnosis
from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessageResponse
from app.services.chat import respond

router = APIRouter(prefix="/chat", tags=["AI Chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diagnosis_context = None
    if body.diagnosis_id:
        result = await db.execute(
            select(Diagnosis).where(Diagnosis.id == body.diagnosis_id)
        )
        diag = result.scalar_one_or_none()
        if diag:
            diagnosis_context = {
                "ai_diagnosis": diag.ai_diagnosis,
                "ai_medications": diag.ai_medications,
                "ai_severity": diag.ai_severity,
            }

    user_msg = ChatMessage(
        user_id=current_user.id,
        diagnosis_id=body.diagnosis_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    reply_text = respond(body.message, diagnosis_context)

    bot_msg = ChatMessage(
        user_id=current_user.id,
        diagnosis_id=body.diagnosis_id,
        role="assistant",
        content=reply_text,
    )
    db.add(bot_msg)
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(bot_msg)

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    history = [ChatMessageResponse.model_validate(m) for m in history_result.scalars().all()]
    history.reverse()

    return ChatResponse(
        reply=ChatMessageResponse.model_validate(bot_msg),
        history=history,
    )


@router.get("/history", response_model=list[ChatMessageResponse])
async def get_history(
    diagnosis_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ChatMessage).where(ChatMessage.user_id == current_user.id)
    if diagnosis_id:
        query = query.where(ChatMessage.diagnosis_id == diagnosis_id)
    query = query.order_by(ChatMessage.created_at.desc()).limit(limit)

    result = await db.execute(query)
    messages = [ChatMessageResponse.model_validate(m) for m in result.scalars().all()]
    messages.reverse()
    return messages
