#!/usr/bin/env python3
"""
Update Cursor MCP Configuration

This script updates the Cursor MCP configuration file (~/.cursor/mcp.json)
to include the Jenkins MCP server configuration.
"""

import json
import os
import sys
from pathlib import Path

# Define the Jenkins MCP server configuration
jenkins_config = {
    "command": "uv",
    "args": [
        "run",
        "-m",
        "src.enhanced_jenkins_mcp"
    ],
    "env": {
        "JENKINS_URL": "http://35.222.64.171:8080/",
        "JENKINS_USERNAME": "admin",
        "JENKINS_API_TOKEN": "111c066e83399b46b288184533f3a11dcd"
    }
}

def main():
    # Get the Cursor MCP configuration file path
    home_dir = Path.home()
    cursor_dir = home_dir / ".cursor"
    mcp_config_path = cursor_dir / "mcp.json"
    
    # Check if the Cursor directory exists
    if not cursor_dir.exists():
        print(f"Error: Cursor directory not found at {cursor_dir}")
        print("Make sure Cursor is installed and has been run at least once.")
        sys.exit(1)
    
    # Create backup of existing config if it exists
    if mcp_config_path.exists():
        with open(mcp_config_path, 'r') as f:
            try:
                config = json.load(f)
                
                # Create backup
                backup_path = mcp_config_path.with_suffix('.json.bak')
                with open(backup_path, 'w') as backup_file:
                    json.dump(config, backup_file, indent=2)
                print(f"Created backup of existing configuration at {backup_path}")
                
                # Add Jenkins MCP server config
                if 'mcpServers' not in config:
                    config['mcpServers'] = {}
                
                # Check if Jenkins config already exists
                if 'jenkins' in config['mcpServers']:
                    replace = input("Jenkins MCP server configuration already exists. Replace it? (y/n): ")
                    if replace.lower() != 'y':
                        print("Operation cancelled.")
                        sys.exit(0)
                
                # Add or update Jenkins config
                config['mcpServers']['jenkins'] = jenkins_config
                
                # Write updated config
                with open(mcp_config_path, 'w') as updated_file:
                    json.dump(config, updated_file, indent=2)
                print(f"Updated Cursor MCP configuration at {mcp_config_path}")
                print("Jenkins MCP server configuration added successfully.")
                print("\nTo use the Jenkins MCP server in Cursor, restart Cursor and use commands like:")
                print("  @jenkins check_jenkins_connection")
                print("  @jenkins list_jobs")
                
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {mcp_config_path}")
                print("Creating a new configuration file.")
                create_new_config(mcp_config_path)
    else:
        print(f"No existing configuration found at {mcp_config_path}")
        create_new_config(mcp_config_path)

def create_new_config(config_path):
    """Create a new MCP configuration file with Jenkins MCP server."""
    new_config = {
        "mcpServers": {
            "jenkins": jenkins_config
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(new_config, f, indent=2)
    
    print(f"Created new Cursor MCP configuration at {config_path}")
    print("Jenkins MCP server configuration added successfully.")
    print("\nTo use the Jenkins MCP server in Cursor, restart Cursor and use commands like:")
    print("  @jenkins check_jenkins_connection")
    print("  @jenkins list_jobs")

if __name__ == "__main__":
    main() 