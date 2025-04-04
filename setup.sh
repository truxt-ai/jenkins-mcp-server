#!/bin/bash
set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -sSf https://install.ultraviolet.dev | sh
    # Add uv to the current shell session
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create the environment
echo "Setting up Jenkins MCP Server environment..."
uv venv

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit the .env file with your Jenkins credentials"
fi

echo ""
echo "Setup complete! You can now run the server with:"
echo "  uv run mcp dev server.py"
echo ""
echo "Or install it in Claude Desktop with:"
echo "  uv run mcp install server.py"
echo ""
echo "Don't forget to update your .env file with your Jenkins credentials!" 