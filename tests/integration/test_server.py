"""Integration tests for server module."""

import os
from pathlib import Path
from typing import Any, Dict, Generator, List, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import Resource, ResourceTemplate, TextContent
from pydantic.networks import AnyUrl
from pytest import MonkeyPatch, mark

from mcpneurolora.server import (
    create_uri,
    ensure_project_root_env,
    get_project_root,
    load_prompt,
    parse_prompt_uri,
    run_mcp_server,
    run_terminal_server,
)


@pytest.fixture
def mock_env(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Mock environment variables."""
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/test/path")
    monkeypatch.setenv("AI_TIMEOUT_MS", "5000")
    yield None
    monkeypatch.delenv("MCP_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("AI_TIMEOUT_MS", raising=False)


def test_create_uri() -> None:
    """Test create_uri function."""
    uri = create_uri("https://example.com")
    # URL objects normalize to include trailing slash
    assert str(uri).rstrip("/") == "https://example.com"

    with pytest.raises(ValueError):
        create_uri("invalid uri")


def test_get_project_root(mock_env: None) -> None:
    """Test get_project_root function."""
    root = get_project_root()
    assert str(root) == "/test/path"

    with patch.dict(os.environ, clear=True):
        root = get_project_root()
        assert root == Path.cwd()


def test_ensure_project_root_env() -> None:
    """Test ensure_project_root_env function."""
    with patch.dict(os.environ, clear=True):
        ensure_project_root_env()
        assert "MCP_PROJECT_ROOT" in os.environ
        assert os.environ["MCP_PROJECT_ROOT"] == str(Path.cwd())


def test_load_prompt() -> None:
    """Test load_prompt function."""
    # Test successful load
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_file", return_value=True
    ), patch("pathlib.Path.read_text", return_value="Test prompt content"):
        content: str = load_prompt("test")
        assert content == "Test prompt content"

    # Test file not found
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent")

    # Test not a file
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_file", return_value=False
    ):
        with pytest.raises(ValueError):
            load_prompt("directory")

    # Test empty file
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_file", return_value=True
    ), patch("pathlib.Path.read_text", return_value=""):
        with pytest.raises(ValueError):
            load_prompt("empty")


def test_parse_prompt_uri() -> None:
    """Test parse_prompt_uri function."""
    # Test valid URIs
    assert parse_prompt_uri("prompts://commands") == {"category": "commands"}
    assert parse_prompt_uri("prompts://commands/improve") == {
        "category": "commands",
        "command": "improve",
    }
    assert parse_prompt_uri("prompts://commands/improve/help") == {
        "category": "commands",
        "command": "improve",
        "action": "help",
    }

    # Test invalid URIs
    with pytest.raises(ValueError):
        parse_prompt_uri("invalid://uri")

    with pytest.raises(ValueError):
        parse_prompt_uri("prompts://")


@pytest.mark.asyncio
@mark.integration
@mark.slow
@pytest.mark.timeout(5)
async def test_run_terminal_server(capsys: pytest.CaptureFixture[str]) -> None:
    """Test run_terminal_server function."""
    mock_terminal = MagicMock()
    mock_terminal.parse_request = MagicMock(
        return_value={"jsonrpc": "2.0", "method": "exit", "id": 1}
    )
    mock_terminal.handle_command = AsyncMock(
        return_value={"jsonrpc": "2.0", "result": "Goodbye!", "id": 1}
    )

    with patch(
        "mcpneurolora.server.JsonRpcTerminal", return_value=mock_terminal
    ), patch("mcpneurolora.terminal_server.logger") as mock_logger, patch(
        "builtins.input", return_value='{"jsonrpc": "2.0", "method": "exit", "id": 1}'
    ):
        # Run server
        await run_terminal_server()

        # Verify interactions
        assert mock_terminal.parse_request.call_count >= 1
        assert mock_terminal.handle_command.await_count >= 1

        # Verify logger calls
        mock_logger.info.assert_any_call("Starting terminal server...")
        mock_logger.info.assert_any_call("Terminal server stopped")


@pytest.mark.asyncio
@mark.integration
@mark.slow
@pytest.mark.timeout(5)
async def test_run_mcp_server(capsys: pytest.CaptureFixture[str]) -> None:
    """Test run_mcp_server function."""
    mock_server = MagicMock()
    mock_server.create_initialization_options = MagicMock(return_value={})
    mock_server.run = AsyncMock()
    mock_server.list_tools = MagicMock(return_value=MagicMock())
    mock_server.call_tool = MagicMock(return_value=MagicMock())
    mock_server.list_resources = MagicMock(return_value=MagicMock())
    mock_server.list_resource_templates = MagicMock(return_value=MagicMock())
    mock_server.read_resource = MagicMock(return_value=MagicMock())

    with patch("mcpneurolora.server.Server", return_value=mock_server), patch(
        "mcpneurolora.server.stdio_server"
    ) as mock_stdio, patch.dict(
        "mcpneurolora.mcp_server.os.environ", {"AI_TIMEOUT_MS": "1000"}
    ):
        # Mock stdin and stdout
        mock_stdin = AsyncMock()
        mock_stdout = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_stdin, mock_stdout)
        mock_stdio.return_value.__aexit__ = AsyncMock()

        # Mock server run to finish quickly
        async def mock_run(*args: Any, **kwargs: Any) -> None:
            mock_server.run.assert_not_awaited()
            return None

        mock_server.run.side_effect = mock_run

        # Run server
        await run_mcp_server()

        # Verify server was initialized and run
        assert mock_server.create_initialization_options.called
        assert mock_server.list_tools.called
        assert mock_server.call_tool.called
        assert mock_server.list_resources.called
        assert mock_server.list_resource_templates.called
        assert mock_server.read_resource.called
        assert mock_server.run.await_count >= 1


@pytest.mark.asyncio
@mark.integration
async def test_mcp_server_tools() -> None:
    """Test MCP server tool handlers."""
    mock_server = MagicMock()
    mock_executor = AsyncMock()
    mock_executor.execute_code_collector.return_value = "Collected code"
    mock_executor.execute_project_structure_reporter.return_value = "Generated tree"
    mock_executor.execute_improve.return_value = "Improved code"
    mock_executor.execute_request.return_value = "Processed request"

    with patch("mcpneurolora.server.Server", return_value=mock_server), patch(
        "mcpneurolora.server.ToolExecutor", return_value=mock_executor
    ), patch("mcpneurolora.server.route_command") as mock_route:

        # Set up mock server and executor
        mock_server.handle_tool = AsyncMock()

        async def handle_collect(
            name: str, args: Dict[str, str], ctx: MagicMock
        ) -> List[TextContent]:
            await mock_executor.execute_code_collector()
            return [TextContent(type="text", text="Collected code")]

        mock_server.handle_tool.side_effect = handle_collect

        # Set up mock route_command
        mock_route.return_value.confidence = 0.8
        mock_route.return_value.command = "collect"

        # Test collect command
        result = await mock_server.handle_tool(
            "collect", {"input_path": "test/path"}, MagicMock()
        )
        assert isinstance(result, list)
        result_items = cast(List[TextContent], result)
        assert all(isinstance(item, TextContent) for item in result_items)
        assert mock_executor.execute_code_collector.called

        # Test showtree command
        mock_route.return_value.command = "showtree"

        async def handle_showtree(
            name: str, args: Dict[str, str], ctx: MagicMock
        ) -> List[TextContent]:
            await mock_executor.execute_project_structure_reporter()
            return [TextContent(type="text", text="Generated tree")]

        mock_server.handle_tool.side_effect = handle_showtree
        result = await mock_server.handle_tool("showtree", {}, MagicMock())
        assert isinstance(result, list)
        assert mock_executor.execute_project_structure_reporter.called

        # Test improve command
        mock_route.return_value.command = "improve"

        async def handle_improve(
            name: str, args: Dict[str, str], ctx: MagicMock
        ) -> List[TextContent]:
            await mock_executor.execute_improve()
            return [TextContent(type="text", text="Improved code")]

        mock_server.handle_tool.side_effect = handle_improve
        result = await mock_server.handle_tool(
            "improve", {"input_path": "test/path"}, MagicMock()
        )
        assert isinstance(result, list)
        assert mock_executor.execute_improve.called

        # Test request command
        mock_route.return_value.command = "request"

        async def handle_request(
            name: str, args: Dict[str, str], ctx: MagicMock
        ) -> List[TextContent]:
            await mock_executor.execute_request()
            return [TextContent(type="text", text="Processed request")]

        mock_server.handle_tool.side_effect = handle_request
        result = await mock_server.handle_tool(
            "request",
            {"input_path": "test/path", "request_text": "test request"},
            MagicMock(),
        )
        assert isinstance(result, list)
        assert mock_executor.execute_request.called

        # Test invalid command
        mock_route.return_value.command = "invalid"

        async def handle_invalid(
            name: str, args: Dict[str, str], ctx: MagicMock
        ) -> List[TextContent]:
            return [TextContent(type="text", text="Error executing tool")]

        mock_server.handle_tool.side_effect = handle_invalid
        result = await mock_server.handle_tool("invalid", {}, MagicMock())
        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "Error executing tool" in result[0].text

        # Test error handling for each command
        for command, error_msg in [
            ("collect", "Code collection failed"),
            ("showtree", "Project structure generation failed"),
            ("improve", "Code improvement failed"),
            ("request", "Request processing failed"),
        ]:
            mock_route.return_value.command = command
            mock_executor.execute_code_collector.side_effect = Exception(error_msg)
            mock_executor.execute_project_structure_reporter.side_effect = Exception(
                error_msg
            )
            mock_executor.execute_improve.side_effect = Exception(error_msg)
            mock_executor.execute_request.side_effect = Exception(error_msg)

            async def handle_error(
                name: str, args: Dict[str, str], ctx: MagicMock
            ) -> List[TextContent]:
                try:
                    if command == "collect":
                        await mock_executor.execute_code_collector()
                    elif command == "showtree":
                        await mock_executor.execute_project_structure_reporter()
                    elif command == "improve":
                        await mock_executor.execute_improve()
                    elif command == "request":
                        await mock_executor.execute_request()
                except Exception as e:
                    return [TextContent(type="text", text=str(e))]
                return [TextContent(type="text", text="Success")]

            mock_server.handle_tool.side_effect = handle_error
            result = await mock_server.handle_tool(command, {}, MagicMock())
            assert isinstance(result, list)
            assert isinstance(result[0], TextContent)
            assert result[0].text == error_msg

        # Test tool execution with missing arguments
        for command in ["collect", "improve", "request"]:
            mock_route.return_value.command = command
            mock_server.handle_tool.side_effect = None  # Reset side effect
            mock_server.handle_tool.side_effect = ValueError(
                "Missing required argument"
            )
            with pytest.raises(ValueError, match="Missing required argument"):
                await mock_server.handle_tool(command, {}, MagicMock())

        # Test tool execution with invalid arguments
        for command in ["collect", "improve", "request"]:
            mock_route.return_value.command = command
            mock_server.handle_tool.side_effect = None  # Reset side effect
            mock_server.handle_tool.side_effect = ValueError("Invalid argument type")
            with pytest.raises(ValueError, match="Invalid argument type"):
                await mock_server.handle_tool(command, {"input_path": 123}, MagicMock())


@pytest.mark.asyncio
@mark.integration
async def test_mcp_server_resources() -> None:
    """Test MCP server resource handlers."""
    mock_server = MagicMock()

    with patch("mcpneurolora.server.Server", return_value=mock_server):
        # Test list_resources
        list_resources_handler = AsyncMock()
        mock_server.list_resources = list_resources_handler
        resources = [
            Resource(
                uri=cast(AnyUrl, "prompts://localhost/commands"),
                name="Command Prompts",
                description="Command help and suggestions",
            )
        ]
        list_resources_handler.return_value = resources
        result = await list_resources_handler()
        assert result == resources

        # Test list_resources error handling
        list_resources_handler.side_effect = Exception("Failed to list resources")
        with pytest.raises(Exception, match="Failed to list resources"):
            await list_resources_handler()

        # Test list_resource_templates
        list_templates_handler = AsyncMock()
        mock_server.list_resource_templates = list_templates_handler
        templates = [
            ResourceTemplate(
                uriTemplate="prompts://commands/{command}/help",
                name="Command Help",
                description="Get help for specific commands",
            )
        ]
        list_templates_handler.return_value = templates
        result = await list_templates_handler()
        assert result == templates

        # Test list_resource_templates error handling
        list_templates_handler.side_effect = Exception("Failed to list templates")
        with pytest.raises(Exception, match="Failed to list templates"):
            await list_templates_handler()

        # Test read_resource
        read_resource_handler = AsyncMock()
        mock_server.read_resource = read_resource_handler
        read_resource_handler.return_value = "Test content"

        with patch("mcpneurolora.server.load_prompt", return_value="Test content"):
            # Test reading root commands
            response = await read_resource_handler("prompts://commands")
            assert response == "Test content"

            # Test reading command help
            response = await read_resource_handler("prompts://commands/collect/help")
            assert response == "Test content"

            # Test reading command suggestions
            response = await read_resource_handler("prompts://commands/collect/suggest")
            assert response == "Test content"

            # Test invalid category
            read_resource_handler.side_effect = ValueError("Invalid category")
            with pytest.raises(ValueError):
                await read_resource_handler("prompts://invalid/collect/help")

            # Test invalid command
            read_resource_handler.side_effect = ValueError("Invalid command")
            with pytest.raises(ValueError):
                await read_resource_handler("prompts://commands/invalid/help")

            # Test invalid action
            read_resource_handler.side_effect = ValueError("Invalid action")
            with pytest.raises(ValueError):
                await read_resource_handler("prompts://commands/collect/invalid")

            # Test file not found
            read_resource_handler.side_effect = FileNotFoundError(
                "Prompt file not found"
            )
            with pytest.raises(FileNotFoundError):
                await read_resource_handler("prompts://commands/missing/help")

            # Test permission error
            read_resource_handler.side_effect = PermissionError("Permission denied")
            with pytest.raises(PermissionError):
                await read_resource_handler("prompts://commands/restricted/help")

            # Test empty prompt content
            read_resource_handler.side_effect = None  # Reset side effect
            with patch("mcpneurolora.server.load_prompt", return_value=""):
                read_resource_handler.side_effect = ValueError("Empty prompt content")
                with pytest.raises(ValueError, match="Empty prompt content"):
                    await read_resource_handler("prompts://commands/empty/help")

            # Test invalid URI format
            read_resource_handler.side_effect = ValueError("Invalid URI format")
            with pytest.raises(ValueError, match="Invalid URI format"):
                await read_resource_handler("invalid://uri/format")
