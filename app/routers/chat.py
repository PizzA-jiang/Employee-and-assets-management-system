"""Chat API with SSE streaming for RAG-based Q&A."""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    ChatRequest, ChatResponse, ChatConversationCreate,
    ChatConversationResponse, ChatConversationDetailResponse, ChatMessageResponse,
)
from pydantic import BaseModel, Field
from app.dependencies import get_current_user
from app.services import rag_engine
from app.services.llm_client import llm_client
from app.services.mcp_client import mcp_client
from app.utils.response import R
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI问答"])

SSE_EOF = "data: [DONE]\n\n"


def _ensure_llm_configured(db: Session):
    api_key = crud.get_ai_config_value(db, "mimo_api_key")
    base_url = crud.get_ai_config_value(db, "mimo_base_url") or "https://llm.goaichat.top/v1"
    model = crud.get_ai_config_value(db, "mimo_model") or "glm-5.2"
    local_endpoint = crud.get_ai_config_value(db, "local_llm_endpoint")
    local_enabled = crud.get_ai_config_value(db, "local_llm_enabled") == "true"
    timeout_val = crud.get_ai_config_value(db, "llm_timeout") or "30"

    try:
        timeout = int(timeout_val)
    except ValueError:
        timeout = 30

    llm_client.configure(
        local_endpoint=local_endpoint,
        local_enabled=local_enabled,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
    )

    servers = crud.get_enabled_mcp_servers(db)
    mcp_client.load_servers(servers)


def _get_rag_params(db: Session) -> dict:
    top_k_val = crud.get_ai_config_value(db, "rag_top_k") or "5"
    ctx_len_val = crud.get_ai_config_value(db, "rag_max_context_len") or "4000"
    try:
        top_k = int(top_k_val)
    except ValueError:
        top_k = 5
    try:
        max_ctx = int(ctx_len_val)
    except ValueError:
        max_ctx = 4000
    return {"top_k": top_k, "max_context_len": max_ctx}


@router.post("/ask", response_model=ChatResponse)
def chat_ask(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_llm_configured(db)
    rag_params = _get_rag_params(db)

    result = rag_engine.rag_query(
        query=data.query,
        db=db,
        top_k=data.top_k or rag_params["top_k"],
        max_context_len=rag_params["max_context_len"],
    )

    return ChatResponse(
        answer=result.answer,
        sources=[
            {"document_title": s["document_title"], "content": s["content"], "score": s["score"]}
            for s in result.sources
        ],
        model_used=result.model_used,
    )


class ChatStreamRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    conversation_id: Optional[int] = Field(None, description="对话ID，为空则创建新对话")


@router.post("/ask/stream")
def chat_ask_stream(
    data: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_llm_configured(db)
    rag_params = _get_rag_params(db)

    # 获取或创建对话
    conv_id = data.conversation_id
    if conv_id:
        conv = crud.get_conversation(db, conv_id, current_user.id)
        if not conv:
            conv = crud.create_conversation(db, current_user.id)
            conv_id = conv.id
    else:
        conv = crud.create_conversation(db, current_user.id, title=data.query[:50])
        conv_id = conv.id

    # 用第一轮用户消息作为对话标题
    msg_count = len(crud.get_conversation_messages(db, conv_id))
    if msg_count == 0:
        crud.update_conversation_title(db, conv_id, data.query[:50])

    # 保存用户消息
    crud.add_chat_message(db, conv_id, "user", data.query)
    db.commit()

    def event_generator():
        answer_parts = []
        sources_data = []
        model_used = ""
        try:
            for event in rag_engine.rag_query_stream(
                query=data.query,
                db=db,
                top_k=data.top_k or rag_params["top_k"],
                max_context_len=rag_params["max_context_len"],
            ):
                if event["type"] == "content":
                    answer_parts.append(event["data"])
                elif event["type"] == "done":
                    done_data = event["data"]
                    sources_data = done_data.get("sources", [])
                    model_used = done_data.get("model_used", "")
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': '流式传输中断'}, ensure_ascii=False)}\n\n"
        else:
            # 流式完成后保存助手消息
            full_answer = "".join(answer_parts)
            if full_answer:
                sources_json = json.dumps(sources_data, ensure_ascii=False) if sources_data else None
                crud.add_chat_message(db, conv_id, "assistant", full_answer, sources_json, model_used or None)
            db.commit()
        yield f"data: {json.dumps({'type': 'conv_id', 'data': conv_id}, ensure_ascii=False)}\n\n"
        yield SSE_EOF

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
def chat_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_llm_configured(db)
    return {
        "model": llm_client.active_model,
        "endpoint": llm_client.active_endpoint,
        "mcp_enabled": mcp_client.is_available,
    }


# ─── 对话历史 ──────────────────────────────────────────────────────
@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convs = crud.get_user_conversations(db, current_user.id)
    items = []
    for c in convs:
        items.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })
    return R.ok(items)


@router.post("/conversations")
def create_conversation(
    data: ChatConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = crud.create_conversation(db, current_user.id, data.title)
    return R.ok({
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    })


@router.get("/conversations/{conv_id}")
def get_conversation_detail(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = crud.get_conversation(db, conv_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = crud.get_conversation_messages(db, conv.id)
    msg_list = []
    for m in messages:
        sources = []
        if m.sources_json:
            try:
                sources = json.loads(m.sources_json)
            except Exception:
                sources = []
        msg_list.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": sources,
            "model_used": m.model_used,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return R.ok({
        "id": conv.id,
        "title": conv.title,
        "messages": msg_list,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    })


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = crud.delete_conversation(db, conv_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="对话不存在")
    db.commit()
    return R.ok()
