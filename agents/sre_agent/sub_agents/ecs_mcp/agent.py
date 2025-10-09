"""
ECS MCP Agent - Amazon ECS monitoring and troubleshooting sub-agent.

Provides read-only ECS operations for monitoring, troubleshooting,
and resource discovery using the AWS ECS MCP Server.
"""

import os
from google.adk.agents import Agent
from ...utils import load_instruction_from_file, get_logger, get_configured_model

# Import MCP modules with error handling
try:
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
    from mcp import StdioServerParameters
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    _mcp_import_error = e

# Configure logging
logger = get_logger(__name__)


def create_ecs_mcp_agent():
    """
    Create ECS MCP agent with monitoring and troubleshooting capabilities.

    Returns:
        Agent: Configured ECS MCP agent or None if creation fails
    """
    # Check if MCP modules are available
    if not MCP_AVAILABLE:
        logger.warning(f"MCP modules not available, skipping ECS MCP agent: {_mcp_import_error}")
        return None

    # Check if ECS MCP agent is disabled via environment variable
    if os.getenv("DISABLE_ECS_MCP_AGENT", "false").lower() == "true":
        logger.info("ECS MCP agent disabled via DISABLE_ECS_MCP_AGENT environment variable")
        return None

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Configure MCP connection to ECS server (READ-ONLY) with timeout and stability fixes
        ecs_mcp_toolset = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="uvx",
                    # Remove @latest to avoid downloads on every startup
                    args=["--from", "awslabs-ecs-mcp-server", "ecs-mcp-server"],
                    env={
                        "AWS_PROFILE": os.getenv("AWS_PROFILE", "default"),
                        "AWS_REGION": os.getenv("AWS_REGION", "us-west-2"),
                        # Fix: Use uppercase log level (research showed case sensitivity)
                        "FASTMCP_LOG_LEVEL": os.getenv("FASTMCP_LOG_LEVEL", "ERROR"), # Must be uppercase
                        "FASTMCP_LOG_FILE": os.getenv("FASTMCP_LOG_FILE", "/tmp/ecs-mcp-server.log"),  # Enable file logging
                        "ALLOW_WRITE": "false",  # Explicitly disable write operations
                        "ALLOW_SENSITIVE_DATA": os.getenv(
                            "ECS_ALLOW_SENSITIVE_DATA", "true"
                        ),  # Enable to see env vars
                        # Add timeout configuration for model loading
                        "INITIALIZATION_TIMEOUT": "60",  # Extended timeout for model download
                    },
                    # Add timeout to prevent hanging during model download
                    timeout=60,  # 60 second timeout for initialization
                )
            ),
            # Configure tools based on discovered available tools
            tool_filter=[
                # Core ECS resource operations (verified working)
                "ecs_resource_management",
                "ecs_troubleshooting_tool",
                # AWS knowledge and documentation tools
                "aws_knowledge_aws___list_regions",
                "aws_knowledge_aws___search_documentation",
                "aws_knowledge_aws___read_documentation",
                # Deployment and monitoring tools
                "get_deployment_status",
                # Keep infrastructure tools for guidance (read-only focused)
                "containerize_app",
                # Optional: Infrastructure creation tools (can remove if not needed)
                "create_ecs_infrastructure",
                "delete_ecs_infrastructure",
            ],
        )

        logger.info("Creating ECS MCP agent with minimal MCPToolset and extended timeout")

        # Test MCP connection first with a simple test
        try:
            # Create agent with minimal tools to test connection stability
            agent = Agent(
                name="ecs_mcp_agent",
                model=get_configured_model(),
                description="Specialized agent for Amazon ECS monitoring, troubleshooting, and read-only resource discovery",
                instruction=load_instruction_from_file(
                    os.path.join(current_dir, "prompts", "system_prompt.md")
                ),
                tools=[ecs_mcp_toolset],
            )
            logger.info("ECS MCP agent created successfully with MCP tools")
            return agent
        except Exception as mcp_error:
            logger.warning(f"MCP connection failed, attempting fallback: {mcp_error}")
            # If MCP fails, create fallback agent
            return _create_fallback_ecs_agent(current_dir)
    except ImportError as e:
        logger.warning(f"Failed to import required MCP modules for ECS agent: {e}")
        return _create_fallback_ecs_agent(current_dir)
    except Exception as e:
        logger.warning(f"Failed to create ECS MCP agent: {e}")
        logger.debug(f"ECS MCP agent creation error details: {e}", exc_info=True)
        return _create_fallback_ecs_agent(current_dir)


def _create_fallback_ecs_agent(current_dir):
    """
    Create a fallback ECS agent without MCP when the MCP server is unavailable.

    This ensures the agent tree remains consistent even when MCP connections fail.
    """
    try:
        logger.info("Creating fallback ECS agent without MCP capabilities")

        fallback_instruction = """You are an ECS operations specialist, but currently the ECS MCP server is unavailable.

I can provide general guidance on:
- ECS architecture and best practices
- Common ECS troubleshooting approaches
- Task definition optimization
- Service configuration recommendations
- Container orchestration concepts

However, I cannot currently:
- List or describe your actual ECS clusters
- Fetch real-time task logs or failures
- Access your specific ECS configurations
- Perform live ECS resource discovery

For active ECS monitoring and troubleshooting, please:
1. Check your AWS console directly
2. Use AWS CLI commands like `aws ecs list-clusters`
3. Contact your system administrator if the ECS monitoring system needs restoration

I'm still here to help with ECS-related questions and guidance!"""

        return Agent(
            name="ecs_mcp_agent",
            model=get_configured_model(),
            description="ECS operations specialist (fallback mode - MCP server unavailable)",
            instruction=fallback_instruction,
            tools=[],  # No tools in fallback mode
        )
    except Exception as e:
        logger.error(f"Failed to create even fallback ECS agent: {e}")
        return None
