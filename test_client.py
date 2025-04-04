#!/usr/bin/env python3
"""
Test client for Enhanced Jenkins MCP Server
This script directly tests the MCP tools without going through a server
"""

import asyncio
import json
from src.enhanced_jenkins_mcp import mcp

async def test_mcp_tools():
    print("Accessing Jenkins MCP...")
    
    # List all tools
    print("\n=== LISTING ALL TOOLS ===")
    tools = await mcp.list_tools()
    tool_names = [tool.name for tool in tools]
    print(f"Found {len(tool_names)} tools:")
    for tool in sorted(tool_names):
        print(f"- {tool}")
    
    # Setup mock tools for demo without actual Jenkins connection
    print("\n=== DEMO TOOL RESPONSES ===")
    mock_responses = {
        "check_jenkins_connection": {
            "status": "success",
            "version": "2.401.1",
            "url": "http://jenkins-demo-url",
            "message": "Successfully connected to Jenkins (DEMO)"
        },
        "list_jobs": [
            {"name": "demo-job-1", "url": "http://jenkins-demo-url/job/demo-job-1/", "color": "blue"},
            {"name": "demo-job-2", "url": "http://jenkins-demo-url/job/demo-job-2/", "color": "red"}
        ],
        "get_build_info": {
            "job_name": "demo-job-1",
            "build_number": 42,
            "status": "SUCCESS",
            "duration": 120,
            "timestamp": 1626962400000,
            "url": "http://jenkins-demo-url/job/demo-job-1/42/",
            "changes": []
        },
        "get_node_info": {
            "name": "demo-node",
            "description": "Demo Jenkins node",
            "offline": False,
            "exec_count": 123,
            "idle": True,
            "temporarily_offline": False
        }
    }
    
    # Print some mock responses for demo purposes
    for tool_name, response in mock_responses.items():
        print(f"\nResponse for {tool_name}:")
        print(json.dumps(response, indent=2))
    
    print("\n=== MCP CORE FUNCTIONS ===")
    print(f"MCP Name: {mcp.name}")
    print(f"MCP Description: Enhanced Jenkins MCP Server")
    
    print("\nTesting complete!")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools()) 