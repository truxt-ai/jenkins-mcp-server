from dataclasses import dataclass
from typing import AsyncIterator, List, Optional
from mcp.server.fastmcp import FastMCP, Context
import jenkins
from contextlib import asynccontextmanager
import os
import sys

def debug_log(message):
    print(f"DEBUG: {message}", file=sys.stderr)

debug_log("Starting Jenkins MCP server...")

@dataclass
class JenkinsContext:
    client: jenkins.Jenkins


@asynccontextmanager
async def jenkins_lifespan(server: FastMCP) -> AsyncIterator[JenkinsContext]:
    """Manage Jenkins client lifecycle"""
    debug_log("Starting Jenkins lifespan")
    try:
        # read .env
        import dotenv
        debug_log("Loading environment variables")
        dotenv.load_dotenv()
        
        # Log environment variables (careful with credentials)
        debug_log(f"JENKINS_URL: {os.environ.get('JENKINS_URL', 'Not set')}")
        debug_log(f"JENKINS_USERNAME: {'Set' if os.environ.get('JENKINS_USERNAME') else 'Not set'}")
        debug_log(f"JENKINS_PASSWORD: {'Set' if os.environ.get('JENKINS_PASSWORD') else 'Not set'}")
        
        jenkins_url = os.environ["JENKINS_URL"]
        username = os.environ["JENKINS_USERNAME"]
        password = os.environ["JENKINS_PASSWORD"]
        
        debug_log(f"Connecting to Jenkins at {jenkins_url}")
        client = jenkins.Jenkins(jenkins_url, username=username, password=password)
        debug_log("Connected to Jenkins successfully")
        yield JenkinsContext(client=client)
    except Exception as e:
        debug_log(f"Error in Jenkins lifespan: {str(e)}")
        # Re-raise the exception to properly handle errors
        raise
    finally:
        debug_log("Exiting Jenkins lifespan")


mcp = FastMCP("jenkins-mcp", lifespan=jenkins_lifespan)
debug_log("FastMCP initialized")

@mcp.tool()
def list_jobs(ctx: Context) -> List[dict]:
    """List all Jenkins jobs"""
    debug_log("Listing Jenkins jobs")
    client = ctx.request_context.lifespan_context.client
    return client.get_jobs()


@mcp.tool()
def trigger_build(
    ctx: Context, job_name: str, parameters: Optional[dict] = None
) -> dict:
    """Trigger a Jenkins build

    Args:
        job_name: Name of the job to build
        parameters: Optional build parameters as a dictionary (e.g. {"param1": "value1"})

    Returns:
        Dictionary containing build information including the build number
    """
    debug_log(f"Triggering build for job: {job_name}")
    if not isinstance(job_name, str):
        raise ValueError(f"job_name must be a string, got {type(job_name)}")
    if parameters is not None and not isinstance(parameters, dict):
        raise ValueError(
            f"parameters must be a dictionary or None, got {type(parameters)}"
        )

    client = ctx.request_context.lifespan_context.client

    # First verify the job exists
    try:
        job_info = client.get_job_info(job_name)
        if not job_info:
            raise ValueError(f"Job {job_name} not found")
    except Exception as e:
        debug_log(f"Error checking job {job_name}: {str(e)}")
        raise ValueError(f"Error checking job {job_name}: {str(e)}")

    # Then try to trigger the build
    try:
        # Get the next build number before triggering
        next_build_number = job_info['nextBuildNumber']
        
        # Trigger the build
        queue_id = client.build_job(job_name, parameters=parameters)
        debug_log(f"Build triggered for {job_name}, queue ID: {queue_id}")
        
        return {
            "status": "triggered",
            "job_name": job_name,
            "queue_id": queue_id,
            "build_number": next_build_number,
            "job_url": job_info["url"],
            "build_url": f"{job_info['url']}{next_build_number}/"
        }
    except Exception as e:
        debug_log(f"Error triggering build for {job_name}: {str(e)}")
        raise ValueError(f"Error triggering build for {job_name}: {str(e)}")


@mcp.tool()
def get_build_status(
    ctx: Context, job_name: str, build_number: Optional[int] = None
) -> dict:
    """Get build status

    Args:
        job_name: Name of the job
        build_number: Build number to check, defaults to latest

    Returns:
        Build information dictionary
    """
    debug_log(f"Getting build status for job: {job_name}, build: {build_number or 'latest'}")
    client = ctx.request_context.lifespan_context.client
    if build_number is None:
        build_number = client.get_job_info(job_name)["lastBuild"]["number"]
    return client.get_build_info(job_name, build_number)


@mcp.tool()
def get_build_logs(
    ctx: Context, job_name: str, build_number: Optional[int] = None
) -> str:
    """Get build logs for a specific build

    Args:
        job_name: Name of the job
        build_number: Build number to get logs for, defaults to latest

    Returns:
        Build logs as a string
    """
    debug_log(f"Getting build logs for job: {job_name}, build: {build_number or 'latest'}")
    client = ctx.request_context.lifespan_context.client
    if build_number is None:
        build_number = client.get_job_info(job_name)["lastBuild"]["number"]
    return client.get_build_console_output(job_name, build_number)


@mcp.tool()
def get_job_config(ctx: Context, job_name: str) -> str:
    """Get Jenkins job configuration in XML format

    Args:
        job_name: Name of the job

    Returns:
        Job configuration as XML string
    """
    debug_log(f"Getting job config for: {job_name}")
    client = ctx.request_context.lifespan_context.client
    return client.get_job_config(job_name)


@mcp.tool()
def get_build_console_output(
    ctx: Context, job_name: str, build_number: Optional[int] = None
) -> str:
    """Get build console output

    Args:
        job_name: Name of the job
        build_number: Build number to get console output for, defaults to latest

    Returns:
        Console output as string
    """
    debug_log(f"Getting console output for job: {job_name}, build: {build_number or 'latest'}")
    client = ctx.request_context.lifespan_context.client
    if build_number is None:
        build_number = client.get_job_info(job_name)["lastBuild"]["number"]
    return client.get_build_console_output(job_name, build_number)


@mcp.tool()
def get_build_history(
    ctx: Context, job_name: str, limit: Optional[int] = 10
) -> List[dict]:
    """Get build history for a job

    Args:
        job_name: Name of the job
        limit: Maximum number of builds to return, defaults to 10

    Returns:
        List of build information dictionaries
    """
    debug_log(f"Getting build history for job: {job_name}, limit: {limit}")
    client = ctx.request_context.lifespan_context.client
    job_info = client.get_job_info(job_name)
    builds = job_info.get("builds", [])[:limit]
    return [client.get_build_info(job_name, build["number"]) for build in builds]


@mcp.tool()
def get_queue_info(ctx: Context) -> List[dict]:
    """Get information about items in the Jenkins queue

    Returns:
        List of queue items with their details
    """
    debug_log("Getting Jenkins queue info")
    client = ctx.request_context.lifespan_context.client
    queue_info = client.get_queue_info()
    return queue_info


@mcp.tool()
def get_node_info(ctx: Context, node_name: Optional[str] = None) -> dict:
    """Get information about Jenkins nodes/slaves

    Args:
        node_name: Name of specific node to get info for, defaults to all nodes

    Returns:
        Dictionary containing node information
    """
    debug_log(f"Getting node info for: {node_name or 'all nodes'}")
    client = ctx.request_context.lifespan_context.client
    if node_name:
        return client.get_node_info(node_name)
    return client.get_nodes()


@mcp.tool()
def get_job_statistics(ctx: Context, job_name: str) -> dict:
    """Get statistics for a Jenkins job

    Args:
        job_name: Name of the job

    Returns:
        Dictionary containing job statistics
    """
    debug_log(f"Getting job statistics for: {job_name}")
    client = ctx.request_context.lifespan_context.client
    job_info = client.get_job_info(job_name)
    return {
        "total_builds": job_info.get("builds", []),
        "last_build_number": job_info.get("lastBuild", {}).get("number"),
        "last_build_status": job_info.get("lastBuild", {}).get("result"),
        "last_build_duration": job_info.get("lastBuild", {}).get("duration"),
        "last_build_timestamp": job_info.get("lastBuild", {}).get("timestamp"),
        "next_build_number": job_info.get("nextBuildNumber"),
        "in_queue": job_info.get("inQueue", False),
        "concurrent_build": job_info.get("concurrentBuild", False),
        "disabled": job_info.get("disabled", False)
    }


@mcp.tool()
def get_build_test_results(
    ctx: Context, job_name: str, build_number: Optional[int] = None
) -> dict:
    """Get test results for a specific build

    Args:
        job_name: Name of the job
        build_number: Build number to get test results for, defaults to latest

    Returns:
        Dictionary containing test results
    """
    debug_log(f"Getting test results for job: {job_name}, build: {build_number or 'latest'}")
    client = ctx.request_context.lifespan_context.client
    if build_number is None:
        build_number = client.get_job_info(job_name)["lastBuild"]["number"]
    build_info = client.get_build_info(job_name, build_number)
    test_report = build_info.get("testReport", {})
    return {
        "total_tests": test_report.get("totalCount", 0),
        "passed_tests": test_report.get("passCount", 0),
        "failed_tests": test_report.get("failCount", 0),
        "skipped_tests": test_report.get("skipCount", 0),
        "test_duration": test_report.get("duration", 0),
        "test_suites": test_report.get("suites", [])
    }


@mcp.tool()
def get_job_health(ctx: Context, job_name: str) -> dict:
    """Get health information for a Jenkins job

    Args:
        job_name: Name of the job

    Returns:
        Dictionary containing job health information
    """
    debug_log(f"Getting job health for: {job_name}")
    client = ctx.request_context.lifespan_context.client
    job_info = client.get_job_info(job_name)
    health_report = job_info.get("healthReport", [])
    return {
        "health_score": job_info.get("healthScore", 0),
        "health_reports": health_report,
        "last_build_status": job_info.get("lastBuild", {}).get("result"),
        "last_build_number": job_info.get("lastBuild", {}).get("number"),
        "last_build_url": job_info.get("lastBuild", {}).get("url"),
        "last_build_timestamp": job_info.get("lastBuild", {}).get("timestamp")
    }


@mcp.tool()
def get_job_status(ctx: Context, job_name: str) -> dict:
    """Get current status of a Jenkins job

    Args:
        job_name: Name of the job

    Returns:
        Dictionary containing job status information
    """
    debug_log(f"Getting job status for: {job_name}")
    client = ctx.request_context.lifespan_context.client
    job_info = client.get_job_info(job_name)
    return {
        "name": job_name,
        "url": job_info["url"],
        "last_build_number": job_info.get("lastBuild", {}).get("number"),
        "last_build_status": job_info.get("lastBuild", {}).get("result"),
        "last_build_url": job_info.get("lastBuild", {}).get("url"),
        "next_build_number": job_info.get("nextBuildNumber"),
        "in_queue": job_info.get("inQueue", False),
        "concurrent_build": job_info.get("concurrentBuild", False),
        "disabled": job_info.get("disabled", False)
    }


@mcp.tool()
def get_build_parameters(
    ctx: Context, job_name: str, build_number: Optional[int] = None
) -> dict:
    """Get parameters used in a specific build

    Args:
        job_name: Name of the job
        build_number: Build number to get parameters for, defaults to latest

    Returns:
        Dictionary of build parameters
    """
    debug_log(f"Getting build parameters for job: {job_name}, build: {build_number or 'latest'}")
    client = ctx.request_context.lifespan_context.client
    if build_number is None:
        build_number = client.get_job_info(job_name)["lastBuild"]["number"]
    build_info = client.get_build_info(job_name, build_number)
    return build_info.get("actions", [{}])[0].get("parameters", [])


# Make sure the MCP server stays running
if __name__ == "__main__":
    mcp.run()
    debug_log("Running MCP server...")