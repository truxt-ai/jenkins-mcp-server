# Enhanced Jenkins MCP Server

This project provides a comprehensive Model Context Protocol (MCP) server for interacting with Jenkins CI/CD systems. It builds upon multiple Python Jenkins API libraries to offer a rich set of Jenkins management features.

## Features

The Enhanced Jenkins MCP Server provides tools for:

- **Connection Management**: Check connections, get Jenkins version, access system info
- **Job Management**: List, create, update, delete, enable/disable, and copy jobs
- **Build Management**: Trigger builds, get build info, console output, and test results
- **Node Management**: List, create, delete, and configure Jenkins nodes (agents)
- **Credential Management**: List, create, and delete Jenkins credentials
- **View Management**: List, create, delete, and configure Jenkins views
- **Plugin Management**: List, get info, and install Jenkins plugins
- **Utility Tools**: Run Groovy scripts, search jobs, get build history

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/jenkins-mcp-server.git
   cd jenkins-mcp-server
   ```

2. Ensure you have Python 3.13+ installed:
   ```bash
   # Check your Python version
   python --version
   
   # If using pyenv, you can install and set Python 3.13
   pyenv install 3.13.2
   pyenv local 3.13.2
   ```

3. Create and activate a virtual environment:
   ```bash
   # Using uv (recommended)
   uv venv .venv
   source .venv/bin/activate
   
   # Or using standard venv
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. Install the required dependencies:
   ```bash
   # Using uv (recommended for faster installation)
   uv pip install -r requirements.txt
   
   # Or using standard pip
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file with your Jenkins credentials:

```
JENKINS_URL=https://your-jenkins-server.example.com
JENKINS_USERNAME=your_username
JENKINS_API_TOKEN=your_api_token
```

You can generate an API token from your Jenkins user configuration page.

## Usage

### Running the MCP Server

To run the enhanced Jenkins MCP server:

```bash
# Make sure your virtual environment is activated
python -m src.enhanced_jenkins_mcp
```

This will start the server on `http://localhost:8000`.

### Using the MCP Server

The MCP server exposes a FastAPI endpoint for each tool. You can call these endpoints using HTTP POST requests.

Example using curl:

```bash
curl -X POST http://localhost:8000/enhanced-jenkins-mcp/tools/check_jenkins_connection \
  -H "Content-Type: application/json" \
  -d '{}'
```

Example using Python requests:

```python
import requests

response = requests.post(
    "http://localhost:8000/enhanced-jenkins-mcp/tools/list_jobs",
    json={"folder_path": ""}
)
jobs = response.json()
print(jobs)
```

## Available Tools

Here are some of the key tools available:

### System and Connection Management

- `check_jenkins_connection`: Check connection to Jenkins server
- `get_jenkins_version`: Get Jenkins version
- `get_jenkins_plugins`: Get installed plugins
- `get_jenkins_system_info`: Get detailed system information
- `restart_jenkins`: Restart the Jenkins server
- `quiet_down_jenkins`: Put Jenkins in quiet mode
- `cancel_quiet_down_jenkins`: Cancel quiet mode

### Job Management

- `list_jobs`: List all Jenkins jobs
- `get_job_info`: Get job information
- `get_job_config`: Get job XML configuration
- `update_job_config`: Update job configuration
- `create_job`: Create a new job
- `delete_job`: Delete a job
- `copy_job`: Copy a job
- `enable_job`: Enable a job
- `disable_job`: Disable a job
- `rename_job`: Rename a job
- `create_folder`: Create a folder

### Build Management

- `build_job`: Trigger a build
- `get_build_info`: Get build information
- `get_last_build_info`: Get last build info
- `get_last_successful_build_info`: Get last successful build
- `get_build_console_output`: Get build console output
- `stop_build`: Stop a running build
- `get_build_test_results`: Get test results
- `get_queue_info`: Get build queue information
- `get_queue_item`: Get queue item information
- `cancel_queue_item`: Cancel a queued build

### Node Management

- `list_nodes`: List all nodes
- `get_node_info`: Get node information
- `create_node`: Create a new node
- `delete_node`: Delete a node
- `enable_node`: Enable a node
- `disable_node`: Disable a node

### Credential Management

- `list_credentials`: List credentials
- `get_credential_domains`: Get credential domains
- `create_credential`: Create a credential
- `delete_credential`: Delete a credential

### View Management

- `list_views`: List all views
- `get_view_info`: Get view information
- `create_view`: Create a new view
- `delete_view`: Delete a view
- `add_job_to_view`: Add a job to a view
- `remove_job_from_view`: Remove a job from a view

### Plugin Management

- `list_plugins`: List installed plugins
- `get_plugin_info`: Get plugin information
- `install_plugin`: Install a plugin

### Utility Tools

- `run_groovy_script`: Run a Groovy script
- `search_jobs`: Search for jobs
- `get_build_history`: Get build history

## Development and Testing

Run tests using pytest:

```bash
# Make sure your virtual environment is activated
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

This project builds upon the following libraries:
- python-jenkins
- fastmcp
- FastAPI

And is inspired by additional Jenkins API wrappers like jenkinsapi, api4jenkins, and aiojenkins.

## Testing with MCP Inspector

You can use the MCP Inspector to visually test and debug the MCP server:

```bash
# Start the MCP server
python -m src.enhanced_jenkins_mcp

# In a new terminal, start the MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8000/enhanced-jenkins-mcp
```

This will start the MCP Inspector UI at http://127.0.0.1:6274, which allows you to:

- Browse and execute all available MCP tools
- View request and response payloads
- Debug server communication issues

For detailed instructions, see [MCP_INSPECTOR_GUIDE.md](./MCP_INSPECTOR_GUIDE.md).

![MCP Inspector](https://github.com/modelcontextprotocol/inspector/raw/main/mcp-inspector.png)

## Using with Cursor

You can integrate this MCP server with Cursor to directly use Jenkins tools within the editor:

1. **Configure Cursor MCP**:
   Run the provided script to add this MCP server to your Cursor configuration:
   ```bash
   ./update_cursor_mcp.py
   ```

2. **Restart Cursor**:
   After updating the configuration, restart Cursor to apply the changes.

3. **Using Jenkins MCP commands in Cursor**:
   Use Jenkins MCP tools directly in Cursor by typing:
   ```
   @jenkins list_jobs
   @jenkins check_jenkins_connection
   @jenkins get_build_info job_name="my-job" build_number=42
   ```

For detailed instructions, see [CURSOR_MCP_SETUP.md](./CURSOR_MCP_SETUP.md). 