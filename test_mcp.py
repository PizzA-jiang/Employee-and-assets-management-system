import asyncio
import os
import sys

os.environ['MYSQL_HOST'] = 'localhost'
os.environ['MYSQL_PORT'] = '3306'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = '101704'
os.environ['MYSQL_DATABASE'] = 'asset_management'

sys.path.insert(0, 'D:\\code')

from mcp_mysql_server import list_tools, call_tool, TOOLS
from mcp.types import CallToolRequestParams
from mcp.server.lowlevel.server import ServerRequestContext


class MockContext:
    pass


async def test():
    ctx = MockContext()
    
    # Test list_tools
    result = await list_tools(ctx, None)
    print('=== Tools ===')
    for tool in result.tools:
        print(f'  {tool.name}: {tool.description}')
    
    # Test query employees
    print('\n=== Query employees ===')
    params = CallToolRequestParams(name='query', arguments={'sql': 'SELECT * FROM employees'})
    result = await call_tool(ctx, params)
    for content in result.content:
        print(content.text)
    
    # Test execute insert user
    print('\n=== Insert user ===')
    params = CallToolRequestParams(
        name='execute', 
        arguments={'sql': "INSERT INTO users (username, email, hashed_password, role, is_active) VALUES (%s, %s, %s, %s, %s)", 'params': ['mcpuser2', 'mcp2@test.com', 'hash', 'employee', 1]}
    )
    result = await call_tool(ctx, params)
    for content in result.content:
        print(content.text)
    
    # Test query the new user
    print('\n=== Query new user ===')
    params = CallToolRequestParams(name='query', arguments={'sql': "SELECT * FROM users WHERE username = %s", 'params': ['mcpuser2']})
    result = await call_tool(ctx, params)
    for content in result.content:
        print(content.text)
    
    # Test tables
    print('\n=== Tables ===')
    params = CallToolRequestParams(name='tables', arguments={})
    result = await call_tool(ctx, params)
    for content in result.content:
        print(content.text)
    
    # Test describe
    print('\n=== Describe users ===')
    params = CallToolRequestParams(name='describe', arguments={'table': 'users'})
    result = await call_tool(ctx, params)
    for content in result.content:
        print(content.text)


if __name__ == '__main__':
    asyncio.run(test())