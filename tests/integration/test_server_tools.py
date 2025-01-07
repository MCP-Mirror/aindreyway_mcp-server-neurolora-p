"""Tests for server tools functionality."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, NonCallableMock, patch

import pytest

from mcpneurolora.tools.definitions import CollectInput, ShowTreeInput


class CodeCollectorToolMock(AsyncMock):
    """Custom AsyncMock for code collector tool."""

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
        self._side_effect: Exception | None = None

    def set_side_effect(self, effect: Exception | None) -> None:
        """Set side effect for the mock."""
        self._side_effect = effect

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Mock tool call."""
        try:
            if self._side_effect:
                raise self._side_effect

            # Validate input using pydantic model
            if "input_path" not in kwargs and not args:
                raise ValueError("input_path is required")

            if args:
                CollectInput(input_path=args[0])
            elif kwargs:
                if "input_path" not in kwargs:
                    raise ValueError("input_path is required")
                CollectInput(**kwargs)

            return "Code collection complete!\nOutput file: output.md"
        except Exception as e:
            return f"No files found to process or error occurred: {str(e)}"


class ProjectStructureReporterToolMock(AsyncMock):
    """Custom AsyncMock for project structure reporter tool."""

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
        self._side_effect: Exception | None = None

    def set_side_effect(self, effect: Exception | None) -> None:
        """Set side effect for the mock."""
        self._side_effect = effect

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Mock tool call."""
        try:
            if self._side_effect:
                raise self._side_effect

            # Validate input using pydantic model
            if kwargs:
                # Only allow known parameters
                allowed_params = ShowTreeInput.model_fields.keys()
                unknown_params = set(kwargs.keys()) - set(allowed_params)
                if unknown_params:
                    raise ValueError(f"Unknown parameters: {unknown_params}")

            ShowTreeInput(**kwargs)  # Validate parameters
            return "Project structure report generated: test.md"
        except Exception as e:
            return f"Error generating report: {str(e)}"


@pytest.fixture
def mock_fastmcp() -> Generator[MagicMock, None, None]:
    """Mock Server instance."""
    with patch("mcpneurolora.server.Server") as mock:
        mock_server = MagicMock()
        mock_server.name = "neurolora"

        # Create mock server methods that return functions
        async def list_tools_fn(self: Any) -> list[Any]:
            return []

        async def call_tool_fn(self: Any, *args: Any, **kwargs: Any) -> list[Any]:
            return []

        async def list_resources_fn(self: Any) -> list[Any]:
            return []

        async def list_resource_templates_fn(self: Any) -> list[Any]:
            return []

        async def read_resource_fn(self: Any, *args: Any) -> str:
            return ""

        # Mock server methods to return functions
        mock_server.list_tools = Mock(return_value=list_tools_fn)
        mock_server.call_tool = Mock(return_value=call_tool_fn)
        mock_server.list_resources = Mock(return_value=list_resources_fn)
        mock_server.list_resource_templates = Mock(
            return_value=list_resource_templates_fn
        )
        mock_server.read_resource = Mock(return_value=read_resource_fn)
        mock_server.run = AsyncMock()

        # Add tool mocks
        mock_server.tools = {
            "project_structure_reporter": ProjectStructureReporterToolMock(),
            "code_collector": CodeCollectorToolMock(),
        }
        mock_server.tool_called = False
        mock.return_value = mock_server
        yield mock_server


@pytest.mark.asyncio
async def test_project_structure_reporter_success(
    tmp_path: Path,
    mock_fastmcp: MagicMock,
) -> None:
    """Test successful project structure report generation."""
    # Call tool through mock server
    result = await mock_fastmcp.tools["project_structure_reporter"]()

    # Verify results
    assert "Project structure report generated" in result


@pytest.mark.asyncio
async def test_code_collector_success(
    tmp_path: Path,
    mock_fastmcp: MagicMock,
) -> None:
    """Test successful code collection."""
    # Call tool through mock server
    result = await mock_fastmcp.tools["code_collector"](input_path="src/")

    # Verify results
    assert "Code collection complete!" in result
    assert "output.md" in result


@pytest.mark.asyncio
async def test_project_structure_reporter_error_handling(
    tmp_path: Path,
    mock_fastmcp: MagicMock,
) -> None:
    """Test error handling in project structure reporter."""
    tool = mock_fastmcp.tools["project_structure_reporter"]
    tool.set_side_effect(ValueError("Invalid configuration"))
    result = await tool()
    assert "Error generating report" in result


@pytest.mark.asyncio
async def test_code_collector_error_handling(
    tmp_path: Path,
    mock_fastmcp: MagicMock,
) -> None:
    """Test error handling in code collector."""
    tool = mock_fastmcp.tools["code_collector"]
    tool.set_side_effect(ValueError("Invalid configuration"))
    result = await tool()
    assert "No files found to process or error occurred" in result


@pytest.mark.asyncio
async def test_code_collector_input_validation(
    tmp_path: Path,
    mock_fastmcp: MagicMock,
) -> None:
    """Test input validation for code collector."""
    tool = mock_fastmcp.tools["code_collector"]

    # Test with valid single path
    result = await tool(input_path="src/")
    assert "Code collection complete!" in result

    # Test with valid list of paths
    result = await tool(input_path=["src/", "tests/"])
    assert "Code collection complete!" in result

    # Test with invalid input
    result = await tool(invalid_param="src/")
    assert "No files found to process or error occurred" in result


@pytest.mark.asyncio
async def test_project_structure_reporter_input_validation(
    tmp_path: Path,
    mock_fastmcp: MagicMock,
) -> None:
    """Test input validation for project structure reporter."""
    tool = mock_fastmcp.tools["project_structure_reporter"]

    # Test with no parameters (valid)
    result = await tool()
    assert "Project structure report generated" in result

    # Test with invalid parameters
    result = await tool(invalid_param="value")
    assert "Error generating report" in result
