"""
ECS MCP Sub-Agent Package.

Provides Amazon ECS monitoring, troubleshooting, and read-only resource discovery
capabilities using the AWS ECS MCP Server.
"""

from .agent import create_ecs_mcp_agent

__all__ = ["create_ecs_mcp_agent"]
