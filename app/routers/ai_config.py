"""AI configuration management API - admin only.

LLM config, MCP server CRUD, RAG settings. All values stored as plain text.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, MCPServer
from app.schemas import (
    AIConfigResponse, AIConfigBatchUpdate,
    AIConfigTestRequest, AIConfigTestResponse,
    MCPServerCreate, MCPServerUpdate, MCPServerResponse, MCPServerTestRequest,
)
from app.dependencies import get_current_admin
from app.services.llm_client import llm_client, LLMError
from app.services.mcp_client import mcp_client
from app.utils.response import R
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-config", tags=["AI配置"])

CONFIG_DESCRIPTIONS = {
    "mimo_api_key": "API密钥",
    "mimo_base_url": "API地址 (OpenAI兼容格式)",
    "mimo_model": "模型名称",
    "local_llm_endpoint": "本地模型端点地址",
    "local_llm_enabled": "是否启用本地模型 (true/false)",
    "rag_top_k": "RAG检索文档块数量",
    "rag_max_context_len": "RAG最大上下文长度",
    "llm_timeout": "LLM调用超时时间(秒)",
}

DEFAULT_CONFIGS = {
    "mimo_api_key": "",
    "mimo_base_url": "https://llm.goaichat.top/v1",
    "mimo_model": "glm-5.2",
    "local_llm_endpoint": "",
    "local_llm_enabled": "false",
    "rag_top_k": "5",
    "rag_max_context_len": "4000",
    "llm_timeout": "30",
}


def _init_default_configs(db: Session, user_id: int):
    for key, default_val in DEFAULT_CONFIGS.items():
        existing = crud.get_ai_config(db, key)
        if not existing:
            crud.upsert_ai_config(
                db, key, default_val,
                description=CONFIG_DESCRIPTIONS.get(key),
                updated_by=user_id,
            )
    db.commit()


def _fix_encrypted_values(db: Session, user_id: int = 1):
    """将数据库中已加密的非敏感字段还原为明文，并修正 URL 格式"""
    from app.services.encryption import decrypt
    sensitive_keys = {"mimo_api_key"}
    all_keys = set(DEFAULT_CONFIGS.keys()) | {"mimo_api_key", "mimo_base_url", "mimo_model",
                                                "local_llm_endpoint", "local_llm_enabled",
                                                "rag_top_k", "rag_max_context_len", "llm_timeout"}
    for key in all_keys - sensitive_keys:
        val = crud.get_ai_config_value(db, key)
        if val and val.startswith("gAAAAA"):
            try:
                plain = decrypt(val)
                crud.upsert_ai_config(db, key, plain, updated_by=user_id)
            except Exception:
                pass
    # 修正 base_url：确保以 /v1 结尾
    url = crud.get_ai_config_value(db, "mimo_base_url")
    if url and not url.rstrip("/").endswith("/v1"):
        fixed = url.rstrip("/") + "/v1"
        crud.upsert_ai_config(db, "mimo_base_url", fixed, updated_by=user_id)
    db.commit()


def _load_config_for_llm(db: Session):
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


def _load_mcp_servers(db: Session):
    servers = crud.get_enabled_mcp_servers(db)
    mcp_client.load_servers(servers)


# ─── LLM Config ──────────────────────────────────────────────────────

@router.get("", response_model=list[AIConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    _init_default_configs(db, current_user.id)
    configs = crud.get_all_ai_configs(db)
    return [AIConfigResponse(
        config_key=c.config_key,
        config_value=c.config_value or "",
        config_type=c.config_type,
        description=c.description,
        updated_at=c.updated_at,
    ) for c in configs]


@router.put("")
def update_configs(
    data: AIConfigBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    for item in data.configs:
        val = item.config_value
        # 自动修正 base_url，确保以 /v1 结尾
        if item.config_key == "mimo_base_url" and val and not val.rstrip("/").endswith("/v1"):
            val = val.rstrip("/") + "/v1"
        existing = crud.get_ai_config(db, item.config_key)
        desc = CONFIG_DESCRIPTIONS.get(item.config_key)
        if existing:
            desc = existing.description or desc
        crud.upsert_ai_config(
            db, item.config_key, val,
            description=desc,
            updated_by=current_user.id,
        )
    db.commit()
    _load_config_for_llm(db)
    return {"message": "配置已保存"}


@router.post("/fix")
def fix_encrypted_values(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    _fix_encrypted_values(db, current_user.id)
    _load_config_for_llm(db)
    return {"message": "已修复加密值"}


@router.post("/test", response_model=AIConfigTestResponse)
def test_config(
    data: AIConfigTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if data.config_key == "mimo_api_key":
        api_key = data.config_value
        base_url = crud.get_ai_config_value(db, "mimo_base_url") or "https://llm.goaichat.top/v1"
        model = crud.get_ai_config_value(db, "mimo_model") or "glm-5.2"
        try:
            llm_client.configure(api_key=api_key, base_url=base_url, model=model, timeout=10)
            resp = llm_client.chat(
                messages=[{"role": "user", "content": "Hello, reply with one word."}],
                timeout=10,
            )
            return AIConfigTestResponse(
                success=True,
                message="API连接成功",
                model_used=resp.get("model", model),
            )
        except LLMError as e:
            return AIConfigTestResponse(success=False, message=str(e))
        except Exception as e:
            return AIConfigTestResponse(success=False, message=f"测试失败: {str(e)}")
    return AIConfigTestResponse(success=False, message="不支持的配置项测试")


@router.get("/models")
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    models = [
        {"id": "glm-5.2", "name": "GLM 5.2", "provider": "zhipu"},
        {"id": "glm-5.3", "name": "GLM 5.3", "provider": "zhipu"},
        {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "provider": "deepseek"},
        {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "provider": "deepseek"},
        {"id": "kimi-k2.6", "name": "Kimi K2.6", "provider": "moonshot"},
        {"id": "kimi-k2.7-code", "name": "Kimi K2.7 Code", "provider": "moonshot"},
        {"id": "qwen3.7-plus", "name": "Qwen 3.7 Plus", "provider": "alibaba"},
        {"id": "qwen3.7-max", "name": "Qwen 3.7 Max", "provider": "alibaba"},
        {"id": "qwen3.8-max", "name": "Qwen 3.8 Max", "provider": "alibaba"},
        {"id": "minimax-m3", "name": "MiniMax M3", "provider": "minimax"},
    ]
    return models


# ─── MCP Server CRUD ─────────────────────────────────────────────────

@router.get("/mcp-servers", response_model=list[MCPServerResponse])
def list_mcp_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    servers = crud.get_all_mcp_servers(db)
    return [MCPServerResponse(
        id=s.id, name=s.name, host=s.host, port=s.port,
        username=s.username, password_masked=s.password or "",
        database=s.database, charset=s.charset,
        is_enabled=s.is_enabled, sort_order=s.sort_order,
        created_at=s.created_at, updated_at=s.updated_at,
    ) for s in servers]


@router.post("/mcp-servers", response_model=MCPServerResponse)
def create_mcp_server(
    data: MCPServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    server = crud.create_mcp_server(
        db, name=data.name, host=data.host, port=data.port,
        username=data.username or "", password=data.password or "",
        database=data.database or "", charset=data.charset,
        is_enabled=data.is_enabled, sort_order=data.sort_order,
    )
    db.commit()
    _load_mcp_servers(db)
    return MCPServerResponse(
        id=server.id, name=server.name, host=server.host, port=server.port,
        username=server.username, password_masked=server.password or "",
        database=server.database, charset=server.charset,
        is_enabled=server.is_enabled, sort_order=server.sort_order,
        created_at=server.created_at, updated_at=server.updated_at,
    )


@router.put("/mcp-servers/{server_id}", response_model=MCPServerResponse)
def update_mcp_server(
    server_id: int,
    data: MCPServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    existing = crud.get_mcp_server(db, server_id)
    if not existing:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")

    update_fields = data.model_dump(exclude_unset=True)
    server = crud.update_mcp_server(db, server_id, **update_fields)
    db.commit()
    _load_mcp_servers(db)

    return MCPServerResponse(
        id=server.id, name=server.name, host=server.host, port=server.port,
        username=server.username, password_masked=server.password or "",
        database=server.database, charset=server.charset,
        is_enabled=server.is_enabled, sort_order=server.sort_order,
        created_at=server.created_at, updated_at=server.updated_at,
    )


@router.delete("/mcp-servers/{server_id}")
def delete_mcp_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    ok = crud.delete_mcp_server(db, server_id)
    if not ok:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    db.commit()
    _load_mcp_servers(db)
    return {"message": "删除成功"}


@router.post("/mcp-servers/test")
def test_mcp_server(
    data: MCPServerTestRequest,
    current_user: User = Depends(get_current_admin),
):
    from app.services.mcp_client import MCPServerConn
    conn = MCPServerConn(
        id=0, name="test", host=data.host, port=data.port,
        username=data.username or "", password=data.password or "",
        database=data.database or "",
    )
    ok, msg = conn.test_connection()
    return {"success": ok, "message": msg}
