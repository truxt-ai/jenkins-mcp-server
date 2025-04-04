"""
Tests for the Enhanced Jenkins MCP Server

This module contains tests for the enhanced_jenkins_mcp.py module, which provides
a comprehensive MCP server for Jenkins CI/CD systems.
"""

import os
import pytest
from unittest.mock import patch

# Import the MCP server to test
from src.enhanced_jenkins_mcp import mcp

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'JENKINS_URL': 'http://mock-jenkins-server:8080',
        'JENKINS_USERNAME': 'admin',
        'JENKINS_API_TOKEN': 'mock-token'
    }):
        yield


# Test basic server setup
@pytest.mark.asyncio
async def test_server_initialization():
    assert mcp.name == "enhanced-jenkins-mcp"
    # Check we have tools
    tools = await mcp.list_tools()
    assert len(tools) > 0
    
    # Print tool names for debugging if needed
    tool_names = [tool.name for tool in tools]
    
    # Verify we have key tools
    key_tools = [
        "list_jobs", 
        "build_job", 
        "get_build_info", 
        "list_nodes", 
        "create_folder",
        "run_groovy_script"
    ]
    
    for tool in key_tools:
        assert tool in tool_names
    
    # We should have at least several tools
    assert len(tools) > 25  # We expect a comprehensive set of tools

# These tests cover the basic functionality and verification of the MCP server.
# Testing tools directly requires setting up a FastAPI application context,
# which is beyond the scope of these simplified tests. 