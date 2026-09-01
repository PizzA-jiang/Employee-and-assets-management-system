"""MCP client supporting multiple database servers with tool calling."""
import json
import logging
from typing import Any, Optional, List, Dict

logger = logging.getLogger(__name__)


class MCPServerConn:
    def __init__(self, id: int, name: str, host: str, port: int,
                 username: str = "", password: str = "", database: str = "",
                 charset: str = "utf8mb4"):
        self.id = id
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.charset = charset

    def _connect(self):
        import pymysql
        kwargs = {"host": self.host, "port": self.port, "charset": self.charset}
        if self.username:
            kwargs["user"] = self.username
        if self.password:
            kwargs["password"] = self.password
        if self.database:
            kwargs["database"] = self.database
        return pymysql.connect(**kwargs)

    def test_connection(self) -> tuple:
        try:
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                return True, "连接成功"
            finally:
                conn.close()
        except Exception as e:
            return False, str(e)

    def query(self, sql: str) -> str:
        sql_stripped = sql.strip().rstrip(";").lstrip().upper()
        if not sql_stripped.startswith("SELECT") and not sql_stripped.startswith("SHOW") and not sql_stripped.startswith("DESCRIBE") and not sql_stripped.startswith("EXPLAIN"):
            return json.dumps({"error": "仅允许 SELECT/SHOW/DESCRIBE/EXPLAIN 查询"})
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                return json.dumps(rows, ensure_ascii=False, default=str)
        finally:
            conn.close()

    def describe_table(self, table: str) -> str:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"DESCRIBE `{table}`")
                rows = cur.fetchall()
                return json.dumps(rows, ensure_ascii=False, default=str)
        finally:
            conn.close()

    def list_tables(self) -> str:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                rows = cur.fetchall()
                return json.dumps([list(r.values())[0] for r in rows], ensure_ascii=False)
        finally:
            conn.close()


class MCPClient:
    def __init__(self):
        self._servers: Dict[int, MCPServerConn] = {}

    def load_servers(self, server_list: list):
        self._servers.clear()
        for s in server_list:
            self._servers[s.id] = MCPServerConn(
                id=s.id, name=s.name, host=s.host, port=s.port,
                username=s.username or "", password=s.password or "",
                database=s.database or "", charset=s.charset or "utf8mb4",
            )

    @property
    def is_available(self) -> bool:
        return len(self._servers) > 0

    def get_server_names(self) -> List[str]:
        return [s.name for s in self._servers.values()]

    def get_tools_schema(self) -> list:
        tools = []
        for sid, server in self._servers.items():
            prefix = f"mcp{sid}"
            tools.extend([
                {
                    "type": "function",
                    "function": {
                        "name": f"{prefix}_query",
                        "description": f"在MCP服务器「{server.name}」上执行SQL查询（只读SELECT）",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "sql": {"type": "string", "description": "SELECT SQL语句"},
                            },
                            "required": ["sql"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": f"{prefix}_list_tables",
                        "description": f"列出MCP服务器「{server.name}」上的所有表",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": f"{prefix}_describe_table",
                        "description": f"查看MCP服务器「{server.name}」上指定表的结构",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "table": {"type": "string", "description": "表名"},
                            },
                            "required": ["table"],
                        },
                    },
                },
            ])
        return tools

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        for prefix, server in [(f"mcp{s.id}", s) for s in self._servers.values()]:
            if tool_name.startswith(prefix):
                try:
                    suffix = tool_name[len(prefix)+1:]
                    if suffix == "query":
                        return server.query(arguments.get("sql", ""))
                    elif suffix == "list_tables":
                        return server.list_tables()
                    elif suffix == "describe_table":
                        return server.describe_table(arguments.get("table", ""))
                except Exception as e:
                    logger.exception(f"MCP tool failed: {tool_name}")
                    return json.dumps({"error": f"MCP执行失败: {str(e)}"})
        return json.dumps({"error": f"未知MCP工具: {tool_name}"})


mcp_client = MCPClient()
