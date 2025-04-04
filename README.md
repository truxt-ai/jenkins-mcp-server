# Jenkins MCP Server

A Model Context Protocol (MCP) server that provides access to Jenkins data and functionality through a standardized interface for LLMs.

## Overview

This project implements an MCP server that connects to Jenkins instances, allowing Large Language Models to:

- Access Jenkins job data as resources
- Execute Jenkins-related operations through tools
- Utilize predefined prompts for common Jenkins interactions

## Installation

### Prerequisites

- Python 3.8+
- Access to a Jenkins instance

### Setting up with `uv`

We recommend using `uv` for managing Python environments:

```bash
# Install uv if you haven't already
curl -sSf https://install.ultraviolet.dev | sh

# Create a new project
uv init jenkins-mcp-server
cd jenkins-mcp-server

# Add dependencies
uv add "mcp[cli]"
uv add python-jenkins
```

### Environment Variables

Create a `.env` file with your Jenkins configuration:

```bash
# Create .env file
cat > .env << EOL
JENKINS_URL=https://your-jenkins-instance.com
JENKINS_USERNAME=your_username
JENKINS_API_TOKEN=your_api_token
EOL

# Load environment variables in your shell
source .env
```

## Usage

### Running the server

Start the server in development mode with:

```bash
uv run mcp dev server.py
```


## Features

- **Resources**: Access Jenkins job configurations, build history, and status information
- **Tools**: Trigger builds, update job configurations, and manage Jenkins tasks
- **Prompts**: Pre-defined interaction patterns for common Jenkins operations


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
