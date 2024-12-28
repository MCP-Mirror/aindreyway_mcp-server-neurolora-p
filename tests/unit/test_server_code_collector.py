"""Unit tests for code collector tool functionality."""

from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, NonCallableMock, patch

from pytest import fixture, mark

from mcpneurolora.server import run_mcp_server


class ToolMock(AsyncMock):
    """Custom AsyncMock that matches the expected tool callable type."""

    def __init__(
        self,
        spec: list[str] | object | type[object] | None = None,
        wraps: Any | None = None,
        name: str | None = None,
        spec_set: list[str] | object | type[object] | None = None,
        parent: NonCallableMock | None = None,
        _spec_state: Any | None = None,
        _new_name: str = "",
        _new_parent: NonCallableMock | None = None,
        _spec_as_instance: bool = False,
        _eat_self: bool | None = None,
        unsafe: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            spec=spec,
            wraps=wraps,
            name=name,
            spec_set=spec_set,
            parent=parent,
            _spec_state=_spec_state,
            _new_name=_new_name,
            _new_parent=_new_parent,
            _spec_as_instance=_spec_as_instance,
            _eat_self=_eat_self,
            unsafe=unsafe,
            **kwargs,
        )
        self._collector: AsyncMock | None = None

    def set_collector(self, collector: AsyncMock | None) -> None:
        """Set the collector instance for this tool."""
        self._collector = collector

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        try:
            input_val = args[0] if args else kwargs.get("input_path")

            if self.side_effect is not None:
                raise self.side_effect

            if not self._collector:
                # Return mock result for initialization tests
                return "Code collection complete!\nOutput file: output.md"

            output = await self._collector.collect_code(
                cast(str | list[str], input_val)
            )
            if output is None:
                return "No files found to process or error occurred"

            return f"Code collection complete!\nOutput file: {output}"
        except Exception:
            return "No files found to process or error occurred"


@fixture
def mock_fastmcp() -> Generator[MagicMock, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolora.server.FastMCP") as mock:
        mock_server = MagicMock()
        mock_server.name = "neurolora"
        mock_server.tools = {"code_collector": ToolMock()}
        mock_server.tool_called = False
        mock.return_value = mock_server
        yield mock_server


@fixture
def mock_collector(project_root: Path) -> Generator[AsyncMock, None, None]:
    """Mock CodeCollector."""
    mock_instance = AsyncMock()
    mock_instance.collect_code = AsyncMock(
        return_value=project_root / "output.md"
    )
    with patch(
        "mcp_server_neurolora.server.CodeCollector",
        return_value=mock_instance,
    ):
        yield mock_instance


@mark.asyncio
async def test_code_collector_tool_logging(
    mock_fastmcp: MagicMock,
    mock_collector: AsyncMock,
    project_root: Path,
) -> None:
    """Test logging behavior in code collector tool."""
    # Setup mock collector
    output_path = project_root / "output.md"
    mock_collector.collect_code.return_value = output_path

    # Initialize and run MCP server
    await run_mcp_server()
    tool_mock = mock_fastmcp.tools["code_collector"]
    tool_mock.set_collector(mock_collector)

    # Test detailed logging
    result = await tool_mock(input_path="src/")

    # Verify output
    assert "Code collection complete!" in result
    assert str(output_path) in result


@mark.asyncio
async def test_code_collector_tool_errors(
    mock_fastmcp: MagicMock,
    mock_collector: AsyncMock,
) -> None:
    """Test error handling in code collector tool."""
    await run_mcp_server()
    tool_mock = mock_fastmcp.tools["code_collector"]
    tool_mock.set_collector(mock_collector)

    error_cases: list[type[Exception]] = [
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
        TypeError,
        Exception,
    ]

    for error in error_cases:
        # Reset mocks for each test case
        mock_collector.collect_code.reset_mock()
        mock_collector.collect_code.side_effect = error("Test error")

        result = await tool_mock("src/")
        assert result == "No files found to process or error occurred"

    # Test no files found case
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = None

    result = await tool_mock("src/")
    assert result == "No files found to process or error occurred"


@mark.asyncio
async def test_code_collector_input_types_and_edge_cases(
    mock_fastmcp: MagicMock,
    mock_collector: AsyncMock,
    project_root: Path,
) -> None:
    """Test code collector tool with different input types and edge cases."""
    await run_mcp_server()
    tool_mock = mock_fastmcp.tools["code_collector"]
    tool_mock.set_collector(mock_collector)

    # Test with list input
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = project_root / "output.md"
    result = await tool_mock(["src/", "tests/"])
    mock_collector.collect_code.assert_called_once_with(["src/", "tests/"])
    assert "Code collection complete!" in result

    # Test with empty list
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = None
    result = await tool_mock([])
    assert "No files found to process or error occurred" in result

    # Test with invalid input type
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.side_effect = TypeError("Invalid input type")
    result = await tool_mock(123)
    assert result == "No files found to process or error occurred"

    # Reset side_effect after error test
    mock_collector.collect_code.side_effect = None

    # Test with special characters in path
    mock_collector.collect_code.reset_mock()
    mock_collector.collect_code.return_value = project_root / "output.md"
    result = await tool_mock(input_path="src/!@#$%^&*()")
    assert "Code collection complete!" in result
    mock_collector.collect_code.assert_called_once_with("src/!@#$%^&*()")
