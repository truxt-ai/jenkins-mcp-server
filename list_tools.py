import asyncio
from src.enhanced_jenkins_mcp import mcp

async def list_tools():
    tools = await mcp.list_tools()
    print('Available tools:')
    for tool in tools:
        print(f'- {tool.name}')

if __name__ == "__main__":
    asyncio.run(list_tools()) 