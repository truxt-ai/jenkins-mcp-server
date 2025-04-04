# Setting Up Jenkins MCP Server in Cursor

This guide explains how to configure and use the Enhanced Jenkins MCP Server with Cursor.

## Configuration Steps

1. **Locate your Cursor MCP configuration file**:
   
   The Cursor MCP configuration is usually located at `~/.cursor/mcp.json`. You can check if this file exists by running:
   ```bash
   cat ~/.cursor/mcp.json
   ```

2. **Add the Jenkins MCP configuration**:
   
   Edit your `~/.cursor/mcp.json` file to include the Jenkins MCP server configuration. You can either:
   
   - Add the Jenkins configuration to your existing file:
     ```json
     {
       "mcpServers": {
         "github": { ... },
         "slack": { ... },
         "teams": { ... },
         "onedrive": { ... },
         "jenkins": {
           "command": "python",
           "args": [
             "-m",
             "src.enhanced_jenkins_mcp"
           ],
           "env": {
             "JENKINS_URL": "https://jenkins-demo-server.example.com",
             "JENKINS_USERNAME": "demo-user",
             "JENKINS_API_TOKEN": "demo-token"
           }
         }
       }
     }
     ```
   
   - Or use the provided `jenkins_mcp_cursor_config.json` file as a reference.

3. **Customize environment variables** (optional):
   
   If you have an actual Jenkins server you want to connect to, update the environment variables in the configuration:
   ```json
   "env": {
     "JENKINS_URL": "https://your-actual-jenkins-server.com",
     "JENKINS_USERNAME": "your-username",
     "JENKINS_API_TOKEN": "your-actual-token"
   }
   ```

## Using Jenkins MCP in Cursor

1. **Restart Cursor**:
   
   After updating the MCP configuration, restart Cursor to apply the changes.

2. **Use Jenkins MCP tools in Cursor**:
   
   You can now use Jenkins MCP tools directly in Cursor. For example:
   
   - To check the Jenkins connection:
     ```
     @jenkins check_jenkins_connection
     ```
   
   - To list Jenkins jobs:
     ```
     @jenkins list_jobs
     ```
   
   - To get information about a specific job:
     ```
     @jenkins get_job_info job_name="my-job"
     ```

3. **Troubleshooting**:
   
   If you encounter issues:
   
   - Check Cursor's logs for error messages
   - Ensure your Python environment is properly set up with all required dependencies
   - Verify that the Jenkins MCP server can run independently using the command:
     ```bash
     python -m src.enhanced_jenkins_mcp
     ```

## Demo Mode vs. Real Jenkins

The configuration provided uses demo mode environment variables, which will return mock responses. This is useful for:

- Testing the MCP integration without a real Jenkins server
- Developing and debugging Jenkins-related features
- Demonstrating Jenkins capabilities

If you have access to a real Jenkins server, replace the environment variables with your actual Jenkins credentials for full functionality.

## Additional Resources

- [Jenkins MCP Server Documentation](./README.md)
- [MCP Inspector Guide](./MCP_INSPECTOR_GUIDE.md)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io) 