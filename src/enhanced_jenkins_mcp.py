"""
Enhanced Jenkins MCP Server

This module provides an enhanced Model Context Protocol (MCP) server that integrates with
Jenkins CI/CD systems through multiple Python Jenkins API wrappers, offering comprehensive
access to Jenkins functionality.

The server leverages python-jenkins as the primary API wrapper but includes functionality
inspired by other wrappers like jenkinsapi, api4jenkins, and aiojenkins.
"""

import os
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import AsyncIterator, List, Dict, Optional, Union, Any, Tuple
from contextlib import asynccontextmanager

# Import MCP server components
from mcp.server.fastmcp import FastMCP, Context

# Import Jenkins API libraries
import jenkins
from jenkins import NotFoundException, JenkinsException
import base64
import requests
from urllib.parse import urljoin
import json

# Import for environment variables
import dotenv


def debug_log(message):
    """Log debug messages to stderr for debugging purposes."""
    print(f"DEBUG: {message}", file=sys.stderr)


@dataclass
class EnhancedJenkinsContext:
    """Context class for holding Jenkins client instances and connection details."""
    client: jenkins.Jenkins
    url: str
    username: str
    password: str  # API token or password


@asynccontextmanager
async def jenkins_lifespan(server: FastMCP) -> AsyncIterator[EnhancedJenkinsContext]:
    """Manage Jenkins client lifecycle and connections.
    
    This context manager initializes the Jenkins client with credentials from
    environment variables, manages the connection lifecycle, and handles
    exceptions during setup and teardown.
    
    Args:
        server: The FastMCP server instance.
        
    Yields:
        EnhancedJenkinsContext: Context object containing the Jenkins client and connection details.
    
    Raises:
        ValueError: If required environment variables are missing or connection fails.
    """
    debug_log("Starting Enhanced Jenkins lifespan")
    try:
        # Load environment variables
        debug_log("Loading environment variables")
        dotenv.load_dotenv()
        
        # Get and validate required environment variables
        env_vars = ["JENKINS_URL", "JENKINS_USERNAME", "JENKINS_API_TOKEN"]
        missing_vars = [var for var in env_vars if not os.environ.get(var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please ensure these are set in your .env file."
            )
        
        # Log environment variables (careful with credentials)
        debug_log(f"JENKINS_URL: {os.environ.get('JENKINS_URL')}")
        debug_log(f"JENKINS_USERNAME: {'Set' if os.environ.get('JENKINS_USERNAME') else 'Not set'}")
        debug_log(f"JENKINS_API_TOKEN: {'Set' if os.environ.get('JENKINS_API_TOKEN') else 'Not set'}")
        
        # Get credentials from environment
        jenkins_url = os.environ["JENKINS_URL"]
        username = os.environ["JENKINS_USERNAME"]
        password = os.environ["JENKINS_API_TOKEN"]  # Actually an API token
        
        # Initialize Jenkins client
        debug_log(f"Connecting to Jenkins at {jenkins_url}")
        client = jenkins.Jenkins(jenkins_url, username=username, password=password)
        
        # Test connection by getting Jenkins version
        try:
            version = client.get_version()
            debug_log(f"Connected to Jenkins successfully (version: {version})")
        except Exception as e:
            raise ValueError(f"Failed to connect to Jenkins: {str(e)}")
        
        # Yield the context with client and connection details
        yield EnhancedJenkinsContext(
            client=client,
            url=jenkins_url,
            username=username,
            password=password
        )
    except Exception as e:
        debug_log(f"Error in Jenkins lifespan: {str(e)}")
        # Re-raise the exception to properly handle errors
        raise
    finally:
        debug_log("Exiting Jenkins lifespan")


# Initialize the MCP server
mcp = FastMCP("enhanced-jenkins-mcp", lifespan=jenkins_lifespan)
debug_log("Enhanced Jenkins MCP server initialized")


# Helper functions
def validate_job_exists(client: jenkins.Jenkins, job_name: str) -> Dict[str, Any]:
    """Validate that a job exists and return its info.
    
    Args:
        client: Jenkins client instance
        job_name: Name of the Jenkins job
        
    Returns:
        Dict containing job information
        
    Raises:
        ValueError: If the job doesn't exist
    """
    try:
        job_info = client.get_job_info(job_name)
        if not job_info:
            raise ValueError(f"Job {job_name} not found")
        return job_info
    except NotFoundException:
        raise ValueError(f"Job {job_name} not found")
    except Exception as e:
        raise ValueError(f"Error checking job {job_name}: {str(e)}")


def handle_folder_path(job_name: str) -> Tuple[str, str]:
    """Handle job names that include folder paths.
    
    Args:
        job_name: Job name, potentially with folder path (e.g., "folder/job")
        
    Returns:
        Tuple of (folder_path, job_name)
    """
    if '/' in job_name:
        parts = job_name.split('/')
        folder_path = '/'.join(parts[:-1])
        base_job_name = parts[-1]
        return folder_path, base_job_name
    return "", job_name


# System and Connection Management Tools

@mcp.tool()
def check_jenkins_connection(ctx: Context) -> Dict[str, Any]:
    """Check connection to Jenkins server and get basic information.
    
    Verifies that the Jenkins server is accessible with the provided credentials
    and returns basic information about the server.
    
    Returns:
        Dictionary containing connection status, Jenkins version, and other info
    """
    debug_log("Checking Jenkins connection")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Get Jenkins version
        version = client.get_version()
        
        # Get more detailed information about the Jenkins server
        try:
            # This is an undocumented python-jenkins API but useful
            system_info = client.get_node_info('(master)')
        except:
            system_info = {}
        
        return {
            "status": "connected",
            "version": version,
            "url": ctx.request_context.lifespan_context.url,
            "username": ctx.request_context.lifespan_context.username,
            "system_info": system_info
        }
    except Exception as e:
        debug_log(f"Error checking Jenkins connection: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def get_jenkins_version(ctx: Context) -> str:
    """Get the version of the Jenkins server.
    
    Returns:
        String with Jenkins version
    """
    debug_log("Getting Jenkins version")
    client = ctx.request_context.lifespan_context.client
    return client.get_version()


@mcp.tool()
def get_jenkins_plugins(ctx: Context, depth: int = 1) -> List[Dict[str, Any]]:
    """Get information about installed Jenkins plugins.
    
    Args:
        depth: Depth of information to retrieve (default: 1)
        
    Returns:
        List of dictionaries containing plugin information
    """
    debug_log(f"Getting Jenkins plugins (depth: {depth})")
    client = ctx.request_context.lifespan_context.client
    return client.get_plugins_info(depth=depth)


@mcp.tool()
def get_jenkins_system_info(ctx: Context) -> Dict[str, Any]:
    """Get detailed system information about the Jenkins server.
    
    This includes information about the Java environment, OS, memory usage, etc.
    
    Returns:
        Dictionary containing system information
    """
    debug_log("Getting Jenkins system information")
    client = ctx.request_context.lifespan_context.client
    
    # Making a direct API call since python-jenkins doesn't have a dedicated method
    url = urljoin(ctx.request_context.lifespan_context.url, "/computer/api/json?depth=1")
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        debug_log(f"Error getting Jenkins system info: {str(e)}")
        raise ValueError(f"Error getting Jenkins system info: {str(e)}")


@mcp.tool()
def restart_jenkins(ctx: Context, safe: bool = True) -> Dict[str, Any]:
    """Restart the Jenkins server.
    
    Args:
        safe: If True, performs a safe restart (waits for builds to complete).
              If False, forces a restart regardless of running builds.
    
    Returns:
        Dictionary with status message
    """
    debug_log(f"Restarting Jenkins (safe: {safe})")
    
    url_endpoint = "/safeRestart" if safe else "/restart"
    url = urljoin(ctx.request_context.lifespan_context.url, url_endpoint)
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Jenkins {'safe ' if safe else ''}restart initiated"
        }
    except Exception as e:
        debug_log(f"Error restarting Jenkins: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def quiet_down_jenkins(ctx: Context) -> Dict[str, Any]:
    """Put Jenkins in quiet mode (no new builds will start).
    
    Returns:
        Dictionary with status message
    """
    debug_log("Setting Jenkins to quiet down mode")
    
    url = urljoin(ctx.request_context.lifespan_context.url, "/quietDown")
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": "Jenkins is now in quiet down mode"
        }
    except Exception as e:
        debug_log(f"Error setting Jenkins to quiet down mode: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
def cancel_quiet_down_jenkins(ctx: Context) -> Dict[str, Any]:
    """Cancel quiet mode in Jenkins (allow new builds to start).
    
    Returns:
        Dictionary with status message
    """
    debug_log("Canceling Jenkins quiet down mode")
    
    url = urljoin(ctx.request_context.lifespan_context.url, "/cancelQuietDown")
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": "Jenkins quiet down mode canceled"
        }
    except Exception as e:
        debug_log(f"Error canceling Jenkins quiet down mode: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


# Job Management Tools

@mcp.tool()
def list_jobs(ctx: Context, folder_path: str = "") -> List[Dict[str, Any]]:
    """List all Jenkins jobs, optionally within a specific folder.
    
    Args:
        folder_path: Optional folder path to list jobs from
        
    Returns:
        List of dictionaries containing job information
    """
    debug_log(f"Listing Jenkins jobs (folder: {folder_path or 'root'})")
    client = ctx.request_context.lifespan_context.client
    
    try:
        if folder_path:
            jobs = client.get_jobs(folder_path)
        else:
            jobs = client.get_jobs()
        
        return jobs
    except Exception as e:
        debug_log(f"Error listing jobs: {str(e)}")
        raise ValueError(f"Error listing jobs: {str(e)}")


@mcp.tool()
def get_job_info(ctx: Context, job_name: str, depth: int = 0) -> Dict[str, Any]:
    """Get detailed information about a specific Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed (e.g., "folder/job")
        depth: Depth of information to retrieve (0-2, higher values include more details)
        
    Returns:
        Dictionary containing job information
    """
    debug_log(f"Getting info for job {job_name} (depth: {depth})")
    client = ctx.request_context.lifespan_context.client
    
    try:
        job_info = client.get_job_info(job_name, depth=depth)
        return job_info
    except NotFoundException:
        raise ValueError(f"Job {job_name} not found")
    except Exception as e:
        debug_log(f"Error getting job info: {str(e)}")
        raise ValueError(f"Error getting job info: {str(e)}")


@mcp.tool()
def get_job_config(ctx: Context, job_name: str) -> str:
    """Get the XML configuration of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        
    Returns:
        String containing the XML configuration
    """
    debug_log(f"Getting configuration for job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        config_xml = client.get_job_config(job_name)
        return config_xml
    except NotFoundException:
        raise ValueError(f"Job {job_name} not found")
    except Exception as e:
        debug_log(f"Error getting job config: {str(e)}")
        raise ValueError(f"Error getting job config: {str(e)}")


@mcp.tool()
def update_job_config(ctx: Context, job_name: str, config_xml: str) -> Dict[str, Any]:
    """Update the XML configuration of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        config_xml: XML configuration string
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Updating configuration for job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Update the job configuration
        client.reconfig_job(job_name, config_xml)
        
        return {
            "status": "success",
            "message": f"Configuration updated for job {job_name}"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error updating job config: {str(e)}")
        raise ValueError(f"Error updating job config: {str(e)}")


@mcp.tool()
def create_job(ctx: Context, job_name: str, config_xml: str) -> Dict[str, Any]:
    """Create a new Jenkins job with the provided configuration.
    
    Args:
        job_name: Name for the new Jenkins job, including folder path if needed
        config_xml: XML configuration string
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Creating new job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Check if job already exists
        try:
            client.get_job_info(job_name)
            raise ValueError(f"Job {job_name} already exists")
        except NotFoundException:
            # This is expected - job should not exist
            pass
        
        # Create the new job
        client.create_job(job_name, config_xml)
        
        return {
            "status": "success",
            "message": f"Job {job_name} created successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error creating job: {str(e)}")
        raise ValueError(f"Error creating job: {str(e)}")


@mcp.tool()
def delete_job(ctx: Context, job_name: str) -> Dict[str, Any]:
    """Delete a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job to delete, including folder path if needed
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Deleting job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Delete the job
        client.delete_job(job_name)
        
        return {
            "status": "success",
            "message": f"Job {job_name} deleted successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error deleting job: {str(e)}")
        raise ValueError(f"Error deleting job: {str(e)}")


@mcp.tool()
def copy_job(ctx: Context, source_job_name: str, target_job_name: str) -> Dict[str, Any]:
    """Copy a Jenkins job to create a new job.
    
    Args:
        source_job_name: Name of the source job to copy from, including folder path if needed
        target_job_name: Name for the new job, including folder path if needed
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Copying job from {source_job_name} to {target_job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the source job exists
        validate_job_exists(client, source_job_name)
        
        # Check if target job already exists
        try:
            client.get_job_info(target_job_name)
            raise ValueError(f"Target job {target_job_name} already exists")
        except NotFoundException:
            # This is expected - target job should not exist
            pass
        
        # Copy the job
        client.copy_job(source_job_name, target_job_name)
        
        return {
            "status": "success",
            "message": f"Job copied from {source_job_name} to {target_job_name}"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error copying job: {str(e)}")
        raise ValueError(f"Error copying job: {str(e)}")


@mcp.tool()
def enable_job(ctx: Context, job_name: str) -> Dict[str, Any]:
    """Enable a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job to enable, including folder path if needed
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Enabling job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        job_info = validate_job_exists(client, job_name)
        
        # Check if already enabled
        if not job_info.get("disabled", False):
            return {
                "status": "info",
                "message": f"Job {job_name} is already enabled"
            }
        
        # Enable the job
        client.enable_job(job_name)
        
        return {
            "status": "success",
            "message": f"Job {job_name} enabled successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error enabling job: {str(e)}")
        raise ValueError(f"Error enabling job: {str(e)}")


@mcp.tool()
def disable_job(ctx: Context, job_name: str) -> Dict[str, Any]:
    """Disable a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job to disable, including folder path if needed
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Disabling job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        job_info = validate_job_exists(client, job_name)
        
        # Check if already disabled
        if job_info.get("disabled", False):
            return {
                "status": "info",
                "message": f"Job {job_name} is already disabled"
            }
        
        # Disable the job
        client.disable_job(job_name)
        
        return {
            "status": "success",
            "message": f"Job {job_name} disabled successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error disabling job: {str(e)}")
        raise ValueError(f"Error disabling job: {str(e)}")


@mcp.tool()
def rename_job(ctx: Context, job_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a Jenkins job.
    
    Args:
        job_name: Current name of the Jenkins job, including folder path if needed
        new_name: New name for the job, including folder path if needed
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Renaming job {job_name} to {new_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the source job exists
        validate_job_exists(client, job_name)
        
        # Check if target name already exists
        try:
            client.get_job_info(new_name)
            raise ValueError(f"A job with name {new_name} already exists")
        except NotFoundException:
            # This is expected - new name should not exist
            pass
        
        # Rename the job
        # python-jenkins doesn't have a direct rename_job method, so we'll make the API call directly
        url = urljoin(ctx.request_context.lifespan_context.url, f"/job/{job_name}/doRename")
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        data = {"newName": new_name}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = requests.post(url, auth=auth, data=data, headers=headers)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Job renamed from {job_name} to {new_name}"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error renaming job: {str(e)}")
        raise ValueError(f"Error renaming job: {str(e)}")


@mcp.tool()
def create_folder(ctx: Context, folder_name: str, description: str = "") -> Dict[str, Any]:
    """Create a new folder in Jenkins.
    
    Args:
        folder_name: Name for the new folder, including parent folder path if needed
        description: Optional description for the folder
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Creating folder {folder_name}")
    client = ctx.request_context.lifespan_context.client
    
    # XML template for a Jenkins folder
    folder_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder">
  <description>{description}</description>
  <properties/>
  <folderViews/>
  <healthMetrics/>
</com.cloudbees.hudson.plugins.folder.Folder>"""
    
    try:
        # Check if folder already exists
        try:
            client.get_job_info(folder_name)
            raise ValueError(f"Folder {folder_name} already exists")
        except NotFoundException:
            # This is expected - folder should not exist
            pass
        
        # Create the folder
        client.create_job(folder_name, folder_xml)
        
        return {
            "status": "success",
            "message": f"Folder {folder_name} created successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error creating folder: {str(e)}")
        raise ValueError(f"Error creating folder: {str(e)}")


# Build Management Tools

@mcp.tool()
def build_job(ctx: Context, job_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build a Jenkins job with optional parameters.
    
    Args:
        job_name: Name of the Jenkins job to build, including folder path if needed
        parameters: Optional dictionary of build parameters (for parameterized builds)
        
    Returns:
        Dictionary with build information including queue item number
    """
    debug_log(f"Building job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Build the job
        queue_item = None
        if parameters:
            debug_log(f"Building with parameters: {parameters}")
            queue_item = client.build_job(job_name, parameters=parameters)
        else:
            queue_item = client.build_job(job_name)
        
        return {
            "status": "success",
            "message": f"Build triggered for job {job_name}",
            "queue_item_number": queue_item
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error building job: {str(e)}")
        raise ValueError(f"Error building job: {str(e)}")


@mcp.tool()
def get_build_info(ctx: Context, job_name: str, build_number: int) -> Dict[str, Any]:
    """Get information about a specific build of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        build_number: Build number to get information for
        
    Returns:
        Dictionary containing build information
    """
    debug_log(f"Getting info for build #{build_number} of job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Get build info
        build_info = client.get_build_info(job_name, build_number)
        return build_info
    except NotFoundException:
        raise ValueError(f"Build #{build_number} not found for job {job_name}")
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error getting build info: {str(e)}")
        raise ValueError(f"Error getting build info: {str(e)}")


@mcp.tool()
def get_last_build_info(ctx: Context, job_name: str) -> Dict[str, Any]:
    """Get information about the last build of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        
    Returns:
        Dictionary containing build information
    """
    debug_log(f"Getting info for last build of job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        job_info = validate_job_exists(client, job_name)
        
        # Check if the job has any builds
        if not job_info.get("lastBuild"):
            raise ValueError(f"Job {job_name} has no builds")
        
        # Get last build number
        last_build_number = job_info["lastBuild"]["number"]
        
        # Get build info
        build_info = client.get_build_info(job_name, last_build_number)
        return build_info
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error getting last build info: {str(e)}")
        raise ValueError(f"Error getting last build info: {str(e)}")


@mcp.tool()
def get_last_successful_build_info(ctx: Context, job_name: str) -> Dict[str, Any]:
    """Get information about the last successful build of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        
    Returns:
        Dictionary containing build information
    """
    debug_log(f"Getting info for last successful build of job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        job_info = validate_job_exists(client, job_name)
        
        # Check if the job has any successful builds
        if not job_info.get("lastSuccessfulBuild"):
            raise ValueError(f"Job {job_name} has no successful builds")
        
        # Get last successful build number
        last_successful_build_number = job_info["lastSuccessfulBuild"]["number"]
        
        # Get build info
        build_info = client.get_build_info(job_name, last_successful_build_number)
        return build_info
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error getting last successful build info: {str(e)}")
        raise ValueError(f"Error getting last successful build info: {str(e)}")


@mcp.tool()
def get_build_console_output(ctx: Context, job_name: str, build_number: int) -> str:
    """Get the console output of a specific build of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        build_number: Build number to get console output for
        
    Returns:
        String containing the console output
    """
    debug_log(f"Getting console output for build #{build_number} of job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Get console output
        output = client.get_build_console_output(job_name, build_number)
        return output
    except NotFoundException:
        raise ValueError(f"Build #{build_number} not found for job {job_name}")
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error getting build console output: {str(e)}")
        raise ValueError(f"Error getting build console output: {str(e)}")


@mcp.tool()
def stop_build(ctx: Context, job_name: str, build_number: int) -> Dict[str, Any]:
    """Stop a running build of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        build_number: Build number to stop
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Stopping build #{build_number} of job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Check if the build exists and is running
        build_info = client.get_build_info(job_name, build_number)
        if not build_info.get("building", False):
            return {
                "status": "info",
                "message": f"Build #{build_number} of job {job_name} is not running"
            }
        
        # Stop the build
        # python-jenkins doesn't have a direct stop_build method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            f"/job/{job_name}/{build_number}/stop"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Build #{build_number} of job {job_name} stopped successfully"
        }
    except NotFoundException:
        raise ValueError(f"Build #{build_number} not found for job {job_name}")
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error stopping build: {str(e)}")
        raise ValueError(f"Error stopping build: {str(e)}")


@mcp.tool()
def get_build_test_results(ctx: Context, job_name: str, build_number: int) -> Dict[str, Any]:
    """Get test results from a specific build of a Jenkins job.
    
    Args:
        job_name: Name of the Jenkins job, including folder path if needed
        build_number: Build number to get test results for
        
    Returns:
        Dictionary containing test results information
    """
    debug_log(f"Getting test results for build #{build_number} of job {job_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the job exists first
        validate_job_exists(client, job_name)
        
        # Check if the build exists
        try:
            client.get_build_info(job_name, build_number)
        except NotFoundException:
            raise ValueError(f"Build #{build_number} not found for job {job_name}")
        
        # Get test results
        # python-jenkins doesn't have a direct get_test_report method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            f"/job/{job_name}/{build_number}/testReport/api/json"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        response = requests.get(url, auth=auth)
        if response.status_code == 404:
            return {
                "status": "info",
                "message": f"No test results found for build #{build_number} of job {job_name}"
            }
            
        response.raise_for_status()
        
        return response.json()
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except requests.exceptions.HTTPError as he:
        if he.response.status_code == 404:
            return {
                "status": "info",
                "message": f"No test results found for build #{build_number} of job {job_name}"
            }
        debug_log(f"HTTP error getting test results: {str(he)}")
        raise ValueError(f"Error getting test results: {str(he)}")
    except Exception as e:
        debug_log(f"Error getting test results: {str(e)}")
        raise ValueError(f"Error getting test results: {str(e)}")


@mcp.tool()
def get_queue_info(ctx: Context) -> List[Dict[str, Any]]:
    """Get information about the Jenkins build queue.
    
    Returns:
        List of dictionaries containing queue item information
    """
    debug_log("Getting Jenkins queue information")
    client = ctx.request_context.lifespan_context.client
    
    try:
        queue_info = client.get_queue_info()
        return queue_info
    except Exception as e:
        debug_log(f"Error getting queue info: {str(e)}")
        raise ValueError(f"Error getting queue info: {str(e)}")


@mcp.tool()
def get_queue_item(ctx: Context, queue_item_number: int) -> Dict[str, Any]:
    """Get information about a specific item in the Jenkins build queue.
    
    Args:
        queue_item_number: Queue item number to get information for
        
    Returns:
        Dictionary containing queue item information
    """
    debug_log(f"Getting info for queue item #{queue_item_number}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        queue_item = client.get_queue_item(queue_item_number)
        return queue_item
    except Exception as e:
        debug_log(f"Error getting queue item: {str(e)}")
        raise ValueError(f"Error getting queue item: {str(e)}")


@mcp.tool()
def cancel_queue_item(ctx: Context, queue_item_number: int) -> Dict[str, Any]:
    """Cancel a queued build in Jenkins.
    
    Args:
        queue_item_number: Queue item number to cancel
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Canceling queue item #{queue_item_number}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Check if the queue item exists
        try:
            client.get_queue_item(queue_item_number)
        except Exception:
            raise ValueError(f"Queue item #{queue_item_number} not found")
        
        # Cancel the queue item
        # python-jenkins doesn't have a direct cancel_queue method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            f"/queue/cancelItem?id={queue_item_number}"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Queue item #{queue_item_number} canceled successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error canceling queue item: {str(e)}")
        raise ValueError(f"Error canceling queue item: {str(e)}")


# Node Management Tools

@mcp.tool()
def list_nodes(ctx: Context) -> List[Dict[str, Any]]:
    """List all Jenkins nodes (agents/slaves).
    
    Returns:
        List of dictionaries containing node information
    """
    debug_log("Listing Jenkins nodes")
    client = ctx.request_context.lifespan_context.client
    
    try:
        nodes = client.get_nodes()
        return nodes
    except Exception as e:
        debug_log(f"Error listing nodes: {str(e)}")
        raise ValueError(f"Error listing nodes: {str(e)}")


@mcp.tool()
def get_node_info(ctx: Context, node_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific Jenkins node.
    
    Args:
        node_name: Name of the Jenkins node
        
    Returns:
        Dictionary containing node information
    """
    debug_log(f"Getting info for node {node_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        node_info = client.get_node_info(node_name)
        return node_info
    except NotFoundException:
        raise ValueError(f"Node {node_name} not found")
    except Exception as e:
        debug_log(f"Error getting node info: {str(e)}")
        raise ValueError(f"Error getting node info: {str(e)}")


@mcp.tool()
def create_node(
    ctx: Context, 
    node_name: str, 
    num_executors: int = 1, 
    node_description: str = "", 
    remote_fs: str = "/var/jenkins", 
    labels: str = "", 
    exclusive: bool = False, 
    launcher: str = "jnlp", 
    launcher_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a new Jenkins node (agent/slave).
    
    Args:
        node_name: Name for the new node
        num_executors: Number of executors for the node
        node_description: Description for the node
        remote_fs: Remote filesystem location for the node
        labels: Labels for the node (comma-separated)
        exclusive: Whether the node should only run jobs with matching labels
        launcher: Launcher method ('jnlp', 'ssh', or 'command')
        launcher_params: Parameters for the launcher (depends on launcher type)
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Creating node {node_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Check if node already exists
        try:
            client.get_node_info(node_name)
            raise ValueError(f"Node {node_name} already exists")
        except NotFoundException:
            # This is expected - node should not exist
            pass
        
        # Set up launcher parameters
        if launcher_params is None:
            launcher_params = {}
        
        # Create the node
        client.create_node(
            node_name,
            nodeDescription=node_description,
            numExecutors=num_executors,
            remoteFS=remote_fs,
            labels=labels,
            exclusive=exclusive,
            launcher=launcher,
            launcher_params=launcher_params
        )
        
        return {
            "status": "success",
            "message": f"Node {node_name} created successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error creating node: {str(e)}")
        raise ValueError(f"Error creating node: {str(e)}")


@mcp.tool()
def delete_node(ctx: Context, node_name: str) -> Dict[str, Any]:
    """Delete a Jenkins node (agent/slave).
    
    Args:
        node_name: Name of the Jenkins node to delete
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Deleting node {node_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the node exists
        try:
            client.get_node_info(node_name)
        except NotFoundException:
            raise ValueError(f"Node {node_name} not found")
        
        # Delete the node
        client.delete_node(node_name)
        
        return {
            "status": "success",
            "message": f"Node {node_name} deleted successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error deleting node: {str(e)}")
        raise ValueError(f"Error deleting node: {str(e)}")


@mcp.tool()
def enable_node(ctx: Context, node_name: str) -> Dict[str, Any]:
    """Enable a Jenkins node (agent/slave).
    
    Args:
        node_name: Name of the Jenkins node to enable
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Enabling node {node_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the node exists
        node_info = None
        try:
            node_info = client.get_node_info(node_name)
        except NotFoundException:
            raise ValueError(f"Node {node_name} not found")
        
        # Check if already enabled
        if not node_info.get("offline", False):
            return {
                "status": "info",
                "message": f"Node {node_name} is already enabled"
            }
        
        # Enable the node
        client.enable_node(node_name)
        
        return {
            "status": "success",
            "message": f"Node {node_name} enabled successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error enabling node: {str(e)}")
        raise ValueError(f"Error enabling node: {str(e)}")


@mcp.tool()
def disable_node(ctx: Context, node_name: str, message: str = "") -> Dict[str, Any]:
    """Disable a Jenkins node (agent/slave).
    
    Args:
        node_name: Name of the Jenkins node to disable
        message: Optional message explaining why the node is being disabled
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Disabling node {node_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Validate that the node exists
        node_info = None
        try:
            node_info = client.get_node_info(node_name)
        except NotFoundException:
            raise ValueError(f"Node {node_name} not found")
        
        # Check if already disabled
        if node_info.get("offline", False):
            return {
                "status": "info",
                "message": f"Node {node_name} is already disabled"
            }
        
        # Disable the node
        client.disable_node(node_name, message)
        
        return {
            "status": "success",
            "message": f"Node {node_name} disabled successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error disabling node: {str(e)}")
        raise ValueError(f"Error disabling node: {str(e)}")


# Credential Management Tools

@mcp.tool()
def list_credentials(ctx: Context, domain: str = "_") -> List[Dict[str, Any]]:
    """List credentials stored in Jenkins.
    
    Args:
        domain: Credentials domain (default is global domain "_")
        
    Returns:
        List of dictionaries containing credential information
    """
    debug_log(f"Listing credentials in domain {domain}")
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        f"/credentials/store/system/domain/{domain}/api/json?depth=1"
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        
        # Extract credentials from the response
        credentials = data.get("credentials", [])
        return credentials
    except requests.exceptions.HTTPError as he:
        if he.response.status_code == 404:
            return []
        debug_log(f"HTTP error listing credentials: {str(he)}")
        raise ValueError(f"Error listing credentials: {str(he)}")
    except Exception as e:
        debug_log(f"Error listing credentials: {str(e)}")
        raise ValueError(f"Error listing credentials: {str(e)}")


@mcp.tool()
def get_credential_domains(ctx: Context) -> List[Dict[str, Any]]:
    """Get a list of credential domains in Jenkins.
    
    Returns:
        List of dictionaries containing credential domain information
    """
    debug_log("Getting credential domains")
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        "/credentials/store/system/api/json?depth=1"
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        
        # Extract domains from the response
        domains = data.get("domains", [])
        return domains
    except Exception as e:
        debug_log(f"Error getting credential domains: {str(e)}")
        raise ValueError(f"Error getting credential domains: {str(e)}")


@mcp.tool()
def create_credential(
    ctx: Context, 
    credential_type: str, 
    id: str, 
    description: str, 
    credential_data: Dict[str, Any],
    domain: str = "_"
) -> Dict[str, Any]:
    """Create a new credential in Jenkins.
    
    Args:
        credential_type: Type of credential ('usernamePassword', 'sshUserPrivateKey', 'string', etc.)
        id: ID for the new credential
        description: Description for the credential
        credential_data: Data specific to the credential type
        domain: Credentials domain (default is global domain "_")
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Creating credential of type {credential_type} with ID {id}")
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        f"/credentials/store/system/domain/{domain}/createCredentials"
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    # Create JSON payload based on credential type
    payload = {
        "": "0",  # Required by Jenkins
        "credentials": {
            "scope": "GLOBAL",
            "id": id,
            "description": description,
        }
    }
    
    # Add credential type-specific data
    if credential_type == "usernamePassword":
        payload["credentials"]["stapler-class"] = "com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl"
        payload["credentials"]["username"] = credential_data.get("username", "")
        payload["credentials"]["password"] = credential_data.get("password", "")
    elif credential_type == "string":
        payload["credentials"]["stapler-class"] = "org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl"
        payload["credentials"]["secret"] = credential_data.get("secret", "")
    elif credential_type == "sshUserPrivateKey":
        payload["credentials"]["stapler-class"] = "com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey"
        payload["credentials"]["username"] = credential_data.get("username", "")
        payload["credentials"]["privateKeySource"] = {"stapler-class": "com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey$DirectEntryPrivateKeySource"}
        payload["credentials"]["privateKeySource"]["privateKey"] = credential_data.get("privateKey", "")
        if "passphrase" in credential_data:
            payload["credentials"]["passphrase"] = credential_data["passphrase"]
    else:
        raise ValueError(f"Unsupported credential type: {credential_type}")
    
    try:
        # Convert the payload to form data
        form_data = {"json": json.dumps(payload)}
        
        # Send the request
        response = requests.post(url, auth=auth, data=form_data)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Credential {id} created successfully"
        }
    except Exception as e:
        debug_log(f"Error creating credential: {str(e)}")
        raise ValueError(f"Error creating credential: {str(e)}")


@mcp.tool()
def delete_credential(ctx: Context, credential_id: str, domain: str = "_") -> Dict[str, Any]:
    """Delete a credential from Jenkins.
    
    Args:
        credential_id: ID of the credential to delete
        domain: Credentials domain (default is global domain "_")
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Deleting credential with ID {credential_id}")
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        f"/credentials/store/system/domain/{domain}/credential/{credential_id}/doDelete"
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Credential {credential_id} deleted successfully"
        }
    except requests.exceptions.HTTPError as he:
        if he.response.status_code == 404:
            raise ValueError(f"Credential {credential_id} not found")
        debug_log(f"HTTP error deleting credential: {str(he)}")
        raise ValueError(f"Error deleting credential: {str(he)}")
    except Exception as e:
        debug_log(f"Error deleting credential: {str(e)}")
        raise ValueError(f"Error deleting credential: {str(e)}")


# View Management Tools

@mcp.tool()
def list_views(ctx: Context) -> List[Dict[str, Any]]:
    """List all views in Jenkins.
    
    Returns:
        List of dictionaries containing view information
    """
    debug_log("Listing Jenkins views")
    client = ctx.request_context.lifespan_context.client
    
    try:
        views = client.get_views()
        return views
    except Exception as e:
        debug_log(f"Error listing views: {str(e)}")
        raise ValueError(f"Error listing views: {str(e)}")


@mcp.tool()
def get_view_info(ctx: Context, view_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific Jenkins view.
    
    Args:
        view_name: Name of the Jenkins view
        
    Returns:
        Dictionary containing view information
    """
    debug_log(f"Getting info for view {view_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        view_info = client.get_view_info(view_name)
        return view_info
    except NotFoundException:
        raise ValueError(f"View {view_name} not found")
    except Exception as e:
        debug_log(f"Error getting view info: {str(e)}")
        raise ValueError(f"Error getting view info: {str(e)}")


@mcp.tool()
def create_view(ctx: Context, view_name: str, view_type: str = "list", view_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a new Jenkins view.
    
    Args:
        view_name: Name for the new view
        view_type: Type of view ('list', 'my', etc.)
        view_config: Additional configuration for the view
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Creating view {view_name} of type {view_type}")
    client = ctx.request_context.lifespan_context.client
    
    # Base XML for a ListView
    list_view_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<hudson.model.ListView>
  <name>{view_name}</name>
  <filterExecutors>false</filterExecutors>
  <filterQueue>false</filterQueue>
  <properties class="hudson.model.View$PropertyList"/>
  <jobNames>
    <comparator class="hudson.util.CaseInsensitiveComparator"/>
  </jobNames>
  <jobFilters/>
  <columns>
    <hudson.views.StatusColumn/>
    <hudson.views.WeatherColumn/>
    <hudson.views.JobColumn/>
    <hudson.views.LastSuccessColumn/>
    <hudson.views.LastFailureColumn/>
    <hudson.views.LastDurationColumn/>
    <hudson.views.BuildButtonColumn/>
  </columns>
  <recurse>false</recurse>
</hudson.model.ListView>"""
    
    # XML for a MyView
    my_view_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<hudson.model.MyView>
  <name>{view_name}</name>
  <filterExecutors>false</filterExecutors>
  <filterQueue>false</filterQueue>
  <properties class="hudson.model.View$PropertyList"/>
</hudson.model.MyView>"""
    
    try:
        # Check if view already exists
        try:
            client.get_view_info(view_name)
            raise ValueError(f"View {view_name} already exists")
        except NotFoundException:
            # This is expected - view should not exist
            pass
        
        # Choose view XML based on type
        if view_type.lower() == "list":
            view_xml = list_view_xml
        elif view_type.lower() == "my":
            view_xml = my_view_xml
        else:
            raise ValueError(f"Unsupported view type: {view_type}")
        
        # Create the view
        # python-jenkins doesn't have a create_view method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            "/createView"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        # Prepare form data
        data = {
            "name": view_name,
            "mode": "hudson.model.ListView" if view_type.lower() == "list" else "hudson.model.MyView",
            "Submit": "OK",
            "json": json.dumps({
                "name": view_name,
                "mode": "hudson.model.ListView" if view_type.lower() == "list" else "hudson.model.MyView"
            })
        }
        
        # Send the request
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        # If we have additional view config, we'd need to set it here
        if view_config:
            # Update view with additional configuration
            # This would depend on the view type and specific configuration
            pass
        
        return {
            "status": "success",
            "message": f"View {view_name} created successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error creating view: {str(e)}")
        raise ValueError(f"Error creating view: {str(e)}")


@mcp.tool()
def delete_view(ctx: Context, view_name: str) -> Dict[str, Any]:
    """Delete a Jenkins view.
    
    Args:
        view_name: Name of the Jenkins view to delete
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Deleting view {view_name}")
    
    try:
        # Check if the view exists
        client = ctx.request_context.lifespan_context.client
        try:
            client.get_view_info(view_name)
        except NotFoundException:
            raise ValueError(f"View {view_name} not found")
        
        # Delete the view
        # python-jenkins doesn't have a delete_view method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            f"/view/{view_name}/doDelete"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        response = requests.post(url, auth=auth)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"View {view_name} deleted successfully"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error deleting view: {str(e)}")
        raise ValueError(f"Error deleting view: {str(e)}")


@mcp.tool()
def add_job_to_view(ctx: Context, view_name: str, job_name: str) -> Dict[str, Any]:
    """Add a job to a Jenkins view.
    
    Args:
        view_name: Name of the Jenkins view
        job_name: Name of the Jenkins job to add
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Adding job {job_name} to view {view_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Check if the view exists
        try:
            client.get_view_info(view_name)
        except NotFoundException:
            raise ValueError(f"View {view_name} not found")
        
        # Check if the job exists
        try:
            client.get_job_info(job_name)
        except NotFoundException:
            raise ValueError(f"Job {job_name} not found")
        
        # Add job to view
        # python-jenkins doesn't have an add_job_to_view method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            f"/view/{view_name}/addJobToView"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        data = {"name": job_name}
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Job {job_name} added to view {view_name}"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error adding job to view: {str(e)}")
        raise ValueError(f"Error adding job to view: {str(e)}")


@mcp.tool()
def remove_job_from_view(ctx: Context, view_name: str, job_name: str) -> Dict[str, Any]:
    """Remove a job from a Jenkins view.
    
    Args:
        view_name: Name of the Jenkins view
        job_name: Name of the Jenkins job to remove
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Removing job {job_name} from view {view_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Check if the view exists
        try:
            client.get_view_info(view_name)
        except NotFoundException:
            raise ValueError(f"View {view_name} not found")
        
        # Remove job from view
        # python-jenkins doesn't have a remove_job_from_view method, so we'll make the API call directly
        url = urljoin(
            ctx.request_context.lifespan_context.url, 
            f"/view/{view_name}/removeJobFromView"
        )
        auth = (
            ctx.request_context.lifespan_context.username, 
            ctx.request_context.lifespan_context.password
        )
        
        data = {"name": job_name}
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Job {job_name} removed from view {view_name}"
        }
    except ValueError as ve:
        # Re-raise the validation error
        raise ve
    except Exception as e:
        debug_log(f"Error removing job from view: {str(e)}")
        raise ValueError(f"Error removing job from view: {str(e)}")


# Plugin Management Tools

@mcp.tool()
def list_plugins(ctx: Context, depth: int = 1) -> List[Dict[str, Any]]:
    """List all installed plugins in Jenkins.
    
    Args:
        depth: Depth of information to retrieve (0-2, higher values include more details)
        
    Returns:
        List of dictionaries containing plugin information
    """
    debug_log(f"Listing Jenkins plugins (depth: {depth})")
    client = ctx.request_context.lifespan_context.client
    
    try:
        plugins = client.get_plugins_info(depth=depth)
        return plugins
    except Exception as e:
        debug_log(f"Error listing plugins: {str(e)}")
        raise ValueError(f"Error listing plugins: {str(e)}")


@mcp.tool()
def get_plugin_info(ctx: Context, plugin_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific Jenkins plugin.
    
    Args:
        plugin_name: Name of the Jenkins plugin
        
    Returns:
        Dictionary containing plugin information
    """
    debug_log(f"Getting info for plugin {plugin_name}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        plugins = client.get_plugins_info(depth=2)
        for plugin in plugins:
            if plugin.get("shortName") == plugin_name:
                return plugin
        
        raise ValueError(f"Plugin {plugin_name} not found")
    except Exception as e:
        debug_log(f"Error getting plugin info: {str(e)}")
        raise ValueError(f"Error getting plugin info: {str(e)}")


@mcp.tool()
def install_plugin(ctx: Context, plugin_name: str, version: str = None) -> Dict[str, Any]:
    """Install a Jenkins plugin.
    
    Args:
        plugin_name: Name of the Jenkins plugin to install
        version: Specific version to install (default is latest)
        
    Returns:
        Dictionary with status information
    """
    debug_log(f"Installing plugin {plugin_name}{' version ' + version if version else ''}")
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        "/pluginManager/installNecessaryPlugins"
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    # Create XML payload for plugin installation
    plugin_xml = f"<jenkins><install plugin=\"{plugin_name}{'@' + version if version else ''}\"/></jenkins>"
    
    try:
        # Send the request
        headers = {"Content-Type": "text/xml"}
        response = requests.post(url, auth=auth, data=plugin_xml, headers=headers)
        response.raise_for_status()
        
        return {
            "status": "success",
            "message": f"Plugin {plugin_name} installation initiated successfully. It may take some time to complete."
        }
    except Exception as e:
        debug_log(f"Error installing plugin: {str(e)}")
        raise ValueError(f"Error installing plugin: {str(e)}")


# Utility Tools

@mcp.tool()
def run_groovy_script(ctx: Context, script: str) -> Dict[str, Any]:
    """Run a Groovy script on the Jenkins server.
    
    Args:
        script: Groovy script to run
        
    Returns:
        Dictionary with script output
    """
    debug_log("Running Groovy script")
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        "/scriptText"
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        # Send the request
        data = {"script": script}
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        return {
            "status": "success",
            "output": response.text
        }
    except Exception as e:
        debug_log(f"Error running Groovy script: {str(e)}")
        raise ValueError(f"Error running Groovy script: {str(e)}")


@mcp.tool()
def search_jobs(ctx: Context, query: str) -> List[Dict[str, Any]]:
    """Search for Jenkins jobs matching a query.
    
    Args:
        query: Search query (name pattern, etc.)
        
    Returns:
        List of dictionaries containing matching job information
    """
    debug_log(f"Searching for jobs matching query: {query}")
    client = ctx.request_context.lifespan_context.client
    
    try:
        # Get all jobs
        all_jobs = []
        
        # First level jobs
        top_jobs = client.get_jobs()
        all_jobs.extend(top_jobs)
        
        # Also search in folders
        for job in top_jobs:
            if job.get("_class", "").find("folder") >= 0:
                folder_name = job["name"]
                try:
                    folder_jobs = client.get_jobs(folder_name)
                    for folder_job in folder_jobs:
                        folder_job["folderPath"] = folder_name
                        all_jobs.append(folder_job)
                except Exception as e:
                    debug_log(f"Error getting jobs in folder {folder_name}: {str(e)}")
        
        # Filter jobs based on query
        matching_jobs = []
        for job in all_jobs:
            job_name = job.get("name", "")
            full_name = job.get("folderPath", "") + "/" + job_name if job.get("folderPath") else job_name
            
            if query.lower() in full_name.lower():
                matching_jobs.append(job)
        
        return matching_jobs
    except Exception as e:
        debug_log(f"Error searching jobs: {str(e)}")
        raise ValueError(f"Error searching jobs: {str(e)}")


@mcp.tool()
def get_build_history(ctx: Context, job_name: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Get build history across all jobs or for a specific job.
    
    Args:
        job_name: Optional name of a specific job to get history for
        limit: Maximum number of builds to return
        
    Returns:
        List of dictionaries containing build information
    """
    debug_log(f"Getting build history{' for job ' + job_name if job_name else ''} (limit: {limit})")
    
    url_path = f"/job/{job_name}/api/json?tree=builds[number,url,result,timestamp,duration,building]{{0,{limit}}}" if job_name else f"/api/json?tree=jobs[name,url,builds[number,url,result,timestamp,duration,building]]{{0,{limit}}}"
    
    url = urljoin(
        ctx.request_context.lifespan_context.url, 
        url_path
    )
    auth = (
        ctx.request_context.lifespan_context.username, 
        ctx.request_context.lifespan_context.password
    )
    
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        
        if job_name:
            return data.get("builds", [])
        else:
            # Combine builds from all jobs
            all_builds = []
            for job in data.get("jobs", []):
                job_name = job.get("name", "")
                for build in job.get("builds", []):
                    build["job"] = job_name
                    all_builds.append(build)
            
            # Sort builds by timestamp (descending)
            all_builds.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            # Limit the number of builds returned
            return all_builds[:limit]
    except Exception as e:
        debug_log(f"Error getting build history: {str(e)}")
        raise ValueError(f"Error getting build history: {str(e)}")


if __name__ == "__main__":
    # Run the MCP server as a standalone application
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    import traceback
    
    try:
        app = FastAPI(title="Enhanced Jenkins MCP Server")
        
        # Add routes for all MCP tools
        debug_log("Setting up FastAPI routes for MCP tools...")
        
        @app.get("/")
        async def root():
            tools = await mcp.list_tools()
            tool_names = [tool.name for tool in tools]
            return {
                "name": mcp.name,
                "description": "Enhanced Jenkins MCP Server",
                "tools": tool_names,
                "version": "1.0.0",
                "mode": "DEMO"
            }
        
        @app.post(f"/{mcp.name}/tools/{{tool_name}}")
        async def handle_tool_call(tool_name: str, request: Request):
            debug_log(f"Processing tool call: {tool_name}")
            try:
                # Get request data
                request_data = await request.json() if await request.body() else {}
                
                # Demo mode - return mock responses for specific tools
                if tool_name == "check_jenkins_connection":
                    return JSONResponse({
                        "status": "success",
                        "version": "2.401.1",
                        "url": "http://jenkins-demo-url",
                        "message": "Successfully connected to Jenkins (DEMO MODE)"
                    })
                elif tool_name == "list_jobs":
                    return JSONResponse([
                        {"name": "demo-job-1", "url": "http://jenkins-demo-url/job/demo-job-1/", "color": "blue"},
                        {"name": "demo-job-2", "url": "http://jenkins-demo-url/job/demo-job-2/", "color": "red"},
                        {"name": "demo-folder/nested-job", "url": "http://jenkins-demo-url/job/demo-folder/job/nested-job/", "color": "blue_anime"}
                    ])
                elif tool_name == "get_build_info":
                    job_name = request_data.get("job_name", "demo-job")
                    build_number = request_data.get("build_number", 1)
                    return JSONResponse({
                        "job_name": job_name,
                        "build_number": build_number,
                        "status": "SUCCESS",
                        "duration": 120,
                        "timestamp": 1626962400000,
                        "url": f"http://jenkins-demo-url/job/{job_name}/{build_number}/",
                        "changes": []
                    })
                elif tool_name == "get_node_info":
                    node_name = request_data.get("node_name", "demo-node")
                    return JSONResponse({
                        "name": node_name,
                        "description": "Demo Jenkins node",
                        "offline": False,
                        "exec_count": 123,
                        "idle": True,
                        "temporarily_offline": False
                    })
                elif tool_name == "get_jenkins_version":
                    return JSONResponse({"version": "2.401.1"})
                elif tool_name == "get_jenkins_plugins":
                    return JSONResponse([
                        {"shortName": "git", "longName": "Git plugin", "version": "4.11.5", "enabled": True},
                        {"shortName": "workflow-aggregator", "longName": "Pipeline", "version": "2.7", "enabled": True},
                        {"shortName": "blueocean", "longName": "Blue Ocean", "version": "1.25.6", "enabled": True}
                    ])
                else:
                    # Check if the tool exists
                    tools = await mcp.list_tools()
                    tool_dict = {tool.name: tool for tool in tools}
                    
                    if tool_name not in tool_dict:
                        return JSONResponse(
                            {"error": f"Tool {tool_name} not found. Available tools: {list(tool_dict.keys())}"},
                            status_code=404
                        )
                    
                    # Generic demo response for other tools
                    return JSONResponse({
                        "status": "demo",
                        "message": f"Tool {tool_name} executed in demo mode. This server is for demonstration purposes only.",
                        "request_data": request_data
                    })
                    
            except Exception as e:
                debug_log(f"Error executing tool {tool_name}: {str(e)}")
                traceback.print_exc()
                return JSONResponse(
                    {"error": f"Error executing tool {tool_name}: {str(e)}"},
                    status_code=500
                )
        
        debug_log("Starting the Enhanced Jenkins MCP server (DEMO MODE)...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
    except Exception as e:
        debug_log(f"Error starting server: {str(e)}")
        traceback.print_exc() 