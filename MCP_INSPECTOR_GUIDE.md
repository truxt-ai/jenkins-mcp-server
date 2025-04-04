# Using MCP Inspector with the Enhanced Jenkins MCP Server

This guide explains how to use the MCP Inspector tool to test and debug the Enhanced Jenkins MCP Server.

## Prerequisites

- Node.js and npm installed
- Python 3.13+ with required packages installed (see README.md)

## Setting Up

1. **Start the MCP Server**:
   ```bash
   # Make sure you're in the virtual environment
   source .venv/bin/activate
   
   # Start the server
   python -m src.enhanced_jenkins_mcp
   ```

2. **Start the MCP Inspector**:
   ```bash
   npx @modelcontextprotocol/inspector http://localhost:8000/enhanced-jenkins-mcp
   ```

3. **Open the MCP Inspector UI**:
   Open your browser to http://127.0.0.1:6274

## Using the Inspector

1. **Connect to the Server**:
   - The URL should already be filled with `http://localhost:8000/enhanced-jenkins-mcp`
   - Click "Connect" to establish a connection

2. **Execute Tools**:
   - Browse the available tools in the left sidebar
   - Click on a tool to select it
   - Enter any required parameters in the JSON editor
   - Click "Execute" to run the tool
   - View the response in the right panel

3. **Test Demo Responses**:
   Since this server is running in demo mode, you can test the following tools:

   - `check_jenkins_connection` - Returns a mock successful connection
   - `list_jobs` - Returns a list of demo jobs
   - `get_build_info` - Returns information about a demo build
   - `get_node_info` - Returns information about a demo node
   - `get_jenkins_version` - Returns a mock Jenkins version
   - `get_jenkins_plugins` - Returns a list of mock plugins

4. **Customize Parameters**:
   For some tools like `get_build_info` and `get_node_info`, you can customize the request by adding parameters:

   For example, with `get_build_info`:
   ```json
   {
     "job_name": "custom-job-name",
     "build_number": 42
   }
   ```

## Troubleshooting

- If you get a "Connection Error" in the Inspector, make sure your MCP server is running
- Check the terminal output of both the server and the Inspector for any error messages
- If the Inspector fails to start, make sure ports 6274 and 6277 are available

## Additional Resources

- [MCP Inspector GitHub Repository](https://github.com/modelcontextprotocol/inspector)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io) 