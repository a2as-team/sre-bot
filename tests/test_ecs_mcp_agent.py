"""
Unit tests for ECS MCP Agent.

Tests the creation and configuration of the ECS MCP agent,
ensuring proper MCPToolset integration and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from agents.sre_agent.sub_agents.ecs_mcp.agent import create_ecs_mcp_agent


class TestECSMCPAgent:
    """Test ECS MCP Agent creation and configuration."""

    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.MCPToolset')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.load_instruction_from_file')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.get_configured_model')
    def test_agent_creation_success(self, mock_get_model, mock_load_instruction, mock_mcp_toolset):
        """Test successful ECS MCP agent creation."""
        # Mock dependencies
        mock_get_model.return_value = "gemini-2.0-flash"
        mock_load_instruction.return_value = "Test instruction"
        mock_toolset_instance = Mock()
        mock_mcp_toolset.return_value = mock_toolset_instance

        # Create agent
        agent = create_ecs_mcp_agent()

        # Verify agent creation
        assert agent is not None
        assert agent.name == "ecs_mcp_agent"
        assert agent.model == "gemini-2.0-flash"
        assert agent.description == "Specialized agent for Amazon ECS monitoring, troubleshooting, and read-only resource discovery"

        # Verify MCPToolset was configured correctly
        mock_mcp_toolset.assert_called_once()
        call_args = mock_mcp_toolset.call_args

        # Check connection params
        assert call_args[1]['connection_params'] is not None

        # Check tool filter contains expected tools
        tool_filter = call_args[1]['tool_filter']
        expected_tools = [
            'get_deployment_status',
            'get_ecs_troubleshooting_guidance',
            'fetch_cloudformation_status',
            'fetch_service_events',
            'fetch_task_failures',
            'fetch_task_logs',
            'detect_image_pull_failures',
            'fetch_network_configuration',
            'list_clusters',
            'describe_clusters',
            'list_services',
            'describe_services',
            'list_tasks',
            'describe_tasks',
            'list_task_definitions',
            'describe_task_definition',
            'list_container_instances',
            'describe_container_instances',
            'list_capacity_providers',
            'describe_capacity_providers'
        ]

        for tool in expected_tools:
            assert tool in tool_filter

    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.MCPToolset')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.get_logger')
    def test_agent_creation_failure(self, mock_logger, mock_mcp_toolset):
        """Test graceful failure when MCP connection fails."""
        # Mock logger
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance

        # Mock MCPToolset to raise exception
        mock_mcp_toolset.side_effect = Exception("Connection failed")

        # Create agent
        agent = create_ecs_mcp_agent()

        # Verify graceful failure
        assert agent is None
        mock_logger_instance.warning.assert_called_once_with(
            "Failed to create ECS MCP agent: Connection failed"
        )

    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.MCPToolset')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.load_instruction_from_file')
    @patch('os.getenv')
    def test_environment_variable_configuration(self, mock_getenv, mock_load_instruction, mock_mcp_toolset):
        """Test that environment variables are properly configured."""
        # Mock environment variables
        def mock_env_side_effect(key, default=None):
            env_vars = {
                'AWS_PROFILE': 'test-profile',
                'AWS_REGION': 'us-west-2',
                'FASTMCP_LOG_LEVEL': 'DEBUG',
                'ECS_ALLOW_SENSITIVE_DATA': 'false'
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = mock_env_side_effect
        mock_load_instruction.return_value = "Test instruction"
        mock_toolset_instance = Mock()
        mock_mcp_toolset.return_value = mock_toolset_instance

        # Create agent
        agent = create_ecs_mcp_agent()

        # Verify agent was created
        assert agent is not None

        # Verify MCPToolset was called with correct environment
        call_args = mock_mcp_toolset.call_args
        server_params = call_args[1]['connection_params'].server_params

        # Check environment variables
        env = server_params.env
        assert env['AWS_PROFILE'] == 'test-profile'
        assert env['AWS_REGION'] == 'us-west-2'
        assert env['FASTMCP_LOG_LEVEL'] == 'DEBUG'
        assert env['ALLOW_WRITE'] == 'false'  # Always false for read-only
        assert env['ALLOW_SENSITIVE_DATA'] == 'false'

    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.MCPToolset')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.load_instruction_from_file')
    def test_read_only_configuration(self, mock_load_instruction, mock_mcp_toolset):
        """Test that the agent is configured for read-only operations."""
        mock_load_instruction.return_value = "Test instruction"
        mock_toolset_instance = Mock()
        mock_mcp_toolset.return_value = mock_toolset_instance

        # Create agent
        agent = create_ecs_mcp_agent()

        # Verify agent was created
        assert agent is not None

        # Verify MCPToolset configuration
        call_args = mock_mcp_toolset.call_args
        server_params = call_args[1]['connection_params'].server_params

        # Verify read-only configuration
        assert server_params.env['ALLOW_WRITE'] == 'false'

        # Verify server command and args
        assert server_params.command == 'uvx'
        assert '--from' in server_params.args
        assert 'awslabs-ecs-mcp-server' in server_params.args
        assert 'ecs-mcp-server' in server_params.args

    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.Agent')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.MCPToolset')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.load_instruction_from_file')
    @patch('agents.sre_agent.sub_agents.ecs_mcp.agent.get_configured_model')
    def test_agent_constructor_parameters(self, mock_get_model, mock_load_instruction, mock_mcp_toolset, mock_agent):
        """Test that Agent constructor is called with correct parameters."""
        # Mock dependencies
        mock_get_model.return_value = "test-model"
        mock_load_instruction.return_value = "test-instruction"
        mock_toolset_instance = Mock()
        mock_mcp_toolset.return_value = mock_toolset_instance
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        # Create agent
        agent = create_ecs_mcp_agent()

        # Verify Agent constructor was called correctly
        mock_agent.assert_called_once_with(
            name="ecs_mcp_agent",
            model="test-model",
            description="Specialized agent for Amazon ECS monitoring, troubleshooting, and read-only resource discovery",
            instruction="test-instruction",
            tools=[mock_toolset_instance]
        )

        # Verify the returned agent
        assert agent == mock_agent_instance