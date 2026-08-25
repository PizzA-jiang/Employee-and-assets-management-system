#!/usr/bin/env python
"""MCP MySQL Server - 新版 MCP SDK 兼容"""
import asyncio
import json
import os
import sys
from typing import Any

import pymysql
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.server import ServerRequestContext
from mcp.types import (
    Tool, TextContent, ListToolsResult, CallToolResult,
    PaginatedRequestParams, CallToolRequestParams
)

# 从环境变量读取配置
config = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", ""),
    "charset": "utf8mb4",
}


def get_conn():
    return pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)


# 定义工具列表
TOOLS = [
    Tool(
        name="query",
        description="执行 SELECT 查询",
        inputSchema={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SELECT 语句"},
                "params": {"type": "array", "items": {}, "default": []},
            },
            "required": ["sql"],
        },
    ),
    Tool(
        name="execute",
        description="执行 INSERT/UPDATE/DELETE",
        inputSchema={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL 语句"},
                "params": {"type": "array", "items": {}, "default": []},
            },
            "required": ["sql"],
        },
    ),
    Tool(
        name="tables",
        description="列出所有表",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="describe",
        description="查看表结构",
        inputSchema={
            "type": "object",
            "properties": {"table": {"type": "string"}},
            "required": ["table"],
        },
    ),
]


async def list_tools(ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


async def call_tool(ctx: ServerRequestContext, params: CallToolRequestParams) -> CallToolResult:
    name = params.name
    arguments = params.arguments or {}
    
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if name == "query":
                cur.execute(arguments["sql"], arguments.get("params", []))
                rows = cur.fetchall()
                return CallToolResult(content=[
                    TextContent(type="text", text=json.dumps(rows, ensure_ascii=False, default=str))
                ])

            elif name == "execute":
                cur.execute(arguments["sql"], arguments.get("params", []))
                conn.commit()
                return CallToolResult(content=[
                    TextContent(type="text", text=f"affected rows: {cur.rowcount}")
                ])

            elif name == "tables":
                cur.execute("SHOW TABLES")
                rows = cur.fetchall()
                return CallToolResult(content=[
                    TextContent(type="text", text=json.dumps([list(r.values())[0] for r in rows], ensure_ascii=False))
                ])

            elif name == "describe":
                cur.execute(f"DESCRIBE `{arguments['table']}`")
                rows = cur.fetchall()
                return CallToolResult(content=[
                    TextContent(type="text", text=json.dumps(rows, ensure_ascii=False, default=str))
                ])

            else:
                return CallToolResult(content=[
                    TextContent(type="text", text=f"Unknown tool: {name}")
                ], isError=True)
    finally:
        conn.close()


# 创建 Server，传入 handlers
app = Server(
    name="mysql",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())