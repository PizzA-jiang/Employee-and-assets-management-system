"""RAG engine combining vector search, tool calling, and LLM generation."""
import json
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from app.services.llm_client import llm_client, LLMError, LLMTimeoutError
from app.services.vector_store import vector_store
from app.services.mcp_client import mcp_client
from app import crud

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是企业资产管理系统的AI助手。请根据以下规则回答用户的问题：

1. 如果参考文档中有相关信息，请基于文档内容回答，并标注引用来源。
2. 如果需要查询员工、资产、流转记录等实时数据，请使用提供的工具函数。
3. 如果参考文档中没有相关信息且不需要查询数据库，请如实说明你不确定，不要编造答案。
4. 回答要简洁、准确、有条理。
5. 使用中文回答。

当前日期：{date}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_employees",
            "description": "查询员工信息，支持按姓名、部门、职位等条件筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "员工姓名（模糊匹配）"},
                    "department": {"type": "string", "description": "部门名称（模糊匹配）"},
                    "position": {"type": "string", "description": "职位（模糊匹配）"},
                    "status": {"type": "integer", "description": "状态: 1=在职, 0=离职"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_assets",
            "description": "查询资产信息，支持按名称、类型、状态等条件筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "资产名称（模糊匹配）"},
                    "asset_type": {
                        "type": "string",
                        "description": "资产类型: computer/phone/monitor/peripheral/furniture/other",
                    },
                    "status": {
                        "type": "string",
                        "description": "状态: available/in_use/maintenance/scrapped",
                    },
                    "location": {"type": "string", "description": "存放位置（模糊匹配）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_asset_logs",
            "description": "查询资产流转记录（领用、归还、调拨、维修、报废等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "员工姓名（模糊匹配）"},
                    "action": {
                        "type": "string",
                        "description": "操作类型: checkout/return/transfer/maintenance_in/maintenance_out/scrap",
                    },
                },
            },
        },
    },
]


@dataclass
class RagResponse:
    answer: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    model_used: str = ""


def _build_context(search_results: list) -> str:
    if not search_results:
        return "（暂无参考文档）"
    parts = []
    for i, r in enumerate(search_results, 1):
        title = getattr(r, "document_title", "") or "未知文档"
        content = getattr(r, "content", "")
        score = getattr(r, "score", 0)
        parts.append(f"[{i}] {title} (相关度: {score:.0%})\n{content}")
    return "\n\n".join(parts)


def _execute_tool(tool_name: str, arguments: dict, db) -> str:
    if tool_name == "query_employees":
        results = crud.query_employees_filtered(db, **arguments)
        return json.dumps(results, ensure_ascii=False, default=str)
    elif tool_name == "query_assets":
        results = crud.query_assets_filtered(db, **arguments)
        return json.dumps(results, ensure_ascii=False, default=str)
    elif tool_name == "query_asset_logs":
        results = crud.query_asset_logs_filtered(db, **arguments)
        return json.dumps(results, ensure_ascii=False, default=str)
    elif tool_name == "mcp_query":
        return mcp_client.execute_tool(tool_name, arguments)
    elif tool_name == "mcp_describe_table":
        return mcp_client.execute_tool(tool_name, arguments)
    return json.dumps({"error": f"未知工具: {tool_name}"})


def _get_all_tools() -> list:
    tools = list(TOOLS)
    if mcp_client.is_available:
        tools.extend(mcp_client.get_tools_schema())
    return tools


def rag_query(query: str, db, top_k: int = 5, max_context_len: int = 4000) -> RagResponse:
    from datetime import date
    today = date.today().isoformat()

    search_results = vector_store.search_by_text(query_text=query, top_k=top_k)
    context = _build_context(search_results)
    if len(context) > max_context_len:
        context = context[:max_context_len] + "\n\n...（上下文已截断）"

    system_msg = SYSTEM_PROMPT.format(date=today) + f"\n\n参考文档：\n{context}"
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": query},
    ]

    tools = _get_all_tools()
    max_rounds = 5

    try:
        for _ in range(max_rounds):
            resp = llm_client.chat(messages=messages, tools=tools if tools else None)
            choice = resp.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "") or ""
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                sources = [
                    {
                        "document_title": getattr(r, "document_title", ""),
                        "content": getattr(r, "content", "")[:200],
                        "score": getattr(r, "score", 0),
                    }
                    for r in search_results
                ]
                return RagResponse(
                    answer=content,
                    sources=sources,
                    model_used=llm_client.active_model,
                )

            messages.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})

            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                try:
                    fn_args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    fn_args = {}

                result = _execute_tool(fn_name, fn_args, db)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })

        sources = [
            {
                "document_title": getattr(r, "document_title", ""),
                "content": getattr(r, "content", "")[:200],
                "score": getattr(r, "score", 0),
            }
            for r in search_results
        ]
        return RagResponse(
            answer="抱歉，处理轮次过多，请简化您的问题后重试。",
            sources=sources,
            model_used=llm_client.active_model,
        )

    except LLMTimeoutError:
        logger.warning("RAG query: LLM timeout")
        return RagResponse(answer="抱歉，AI服务响应超时，请稍后重试。", model_used=llm_client.active_model)
    except LLMError as e:
        logger.error(f"RAG query: LLM error: {e}")
        return RagResponse(answer=f"抱歉，AI服务暂时不可用：{e}", model_used=llm_client.active_model)
    except Exception as e:
        logger.exception(f"RAG query failed: {e}")
        return RagResponse(answer="抱歉，处理过程中出现错误，请稍后重试。")


def rag_query_stream(query: str, db, top_k: int = 5, max_context_len: int = 4000):
    from datetime import date
    today = date.today().isoformat()

    search_results = vector_store.search_by_text(query_text=query, top_k=top_k)
    context = _build_context(search_results)
    if len(context) > max_context_len:
        context = context[:max_context_len] + "\n\n...（上下文已截断）"

    system_msg = SYSTEM_PROMPT.format(date=today) + f"\n\n参考文档：\n{context}"
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": query},
    ]

    tools = _get_all_tools()

    try:
        for chunk in llm_client.chat_stream(messages=messages, tools=tools if tools else None):
            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            if content:
                yield {"type": "content", "data": content}

            finish_reason = choice.get("finish_reason")
            if finish_reason == "stop":
                sources = [
                    {
                        "document_title": getattr(r, "document_title", ""),
                        "content": getattr(r, "content", "")[:200],
                        "score": getattr(r, "score", 0),
                    }
                    for r in search_results
                ]
                yield {"type": "done", "data": {"sources": sources, "model_used": llm_client.active_model}}
                return

            tool_calls = delta.get("tool_calls")
            if tool_calls:
                yield {"type": "tool_call", "data": tool_calls}
                full_message = {"role": "assistant", "content": None, "tool_calls": tool_calls}
                messages.append(full_message)

                for tc in tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    try:
                        fn_args = json.loads(fn.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        fn_args = {}
                    result = _execute_tool(fn_name, fn_args, db)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": result,
                    })

                for follow_chunk in llm_client.chat_stream(messages=messages, tools=tools if tools else None):
                    fc = follow_chunk.get("choices", [{}])[0]
                    fd = fc.get("delta", {})
                    fc_content = fd.get("content", "")
                    if fc_content:
                        yield {"type": "content", "data": fc_content}
                    if fc.get("finish_reason") == "stop":
                        sources = [
                            {
                                "document_title": getattr(r, "document_title", ""),
                                "content": getattr(r, "content", "")[:200],
                                "score": getattr(r, "score", 0),
                            }
                            for r in search_results
                        ]
                        yield {"type": "done", "data": {"sources": sources, "model_used": llm_client.active_model}}
                        return
                return

    except LLMTimeoutError:
        yield {"type": "error", "data": "AI服务响应超时，请稍后重试。"}
    except LLMError as e:
        yield {"type": "error", "data": f"AI服务暂时不可用：{e}"}
    except Exception as e:
        logger.exception(f"RAG stream query failed: {e}")
        yield {"type": "error", "data": "处理过程中出现错误，请稍后重试。"}
