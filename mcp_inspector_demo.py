#!/usr/bin/env python3
"""
MCP Inspector Demo Script

This script demonstrates how to use the MCP Inspector to test and interact with
the Enhanced Jenkins MCP Server. The MCP Inspector is a utility that allows
manual testing of MCP tools through a web interface.

Installation:
    pip install mcp-inspector

Usage:
    python mcp_inspector_demo.py
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from src.enhanced_jenkins_mcp import mcp

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Render a simple HTML page with instructions for using MCP Inspector."""
    tools = await mcp.list_tools()
    tool_names = [tool.name for tool in tools]
    
    tool_list_html = "\n".join([f"<li><code>{name}</code></li>" for name in sorted(tool_names)])
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced Jenkins MCP Server - Inspector Demo</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1, h2 {{ color: #333; }}
            code {{ background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
            pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .alert {{ background-color: #fff3cd; border: 1px solid #ffecb5; color: #856404; padding: 10px; border-radius: 5px; }}
            ul {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        <h1>Enhanced Jenkins MCP Server - Inspector Demo</h1>
        
        <div class="alert">
            <strong>Note:</strong> This is a demo version running in local mode without an actual Jenkins connection.
        </div>
        
        <h2>Using MCP Inspector</h2>
        <p>To test this server with MCP Inspector:</p>
        <ol>
            <li>Install MCP Inspector: <code>pip install mcp-inspector</code></li>
            <li>With this server running, open a new terminal</li>
            <li>Run: <code>mcp-inspector http://localhost:8000/enhanced-jenkins-mcp</code></li>
            <li>The inspector will open in your web browser</li>
        </ol>
        
        <h2>Available Tools ({len(tool_names)})</h2>
        <ul>
            {tool_list_html}
        </ul>
        
        <h2>Sample API Call</h2>
        <p>Example of how to call a tool using curl:</p>
        <pre>curl -X POST http://localhost:8000/enhanced-jenkins-mcp/tools/check_jenkins_connection \\
     -H "Content-Type: application/json" \\
     -d '{{}}'</pre>
     
        <h2>Server Status</h2>
        <p>MCP Name: <code>{mcp.name}</code></p>
        <p>Server Mode: <code>DEMO</code> (not connected to an actual Jenkins instance)</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    print("Starting MCP Inspector demo server on http://localhost:8000")
    print("To use MCP Inspector, open another terminal and run:")
    print("  mcp-inspector http://localhost:8000/enhanced-jenkins-mcp")
    uvicorn.run(app, host="0.0.0.0", port=8000) 