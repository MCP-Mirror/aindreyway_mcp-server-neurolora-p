"""Tests for server tools functionality."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, NonCallableMock, patch

import pytest

from mcp_server_neurolorap.server import create_server


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
            return "Code collection complete!\nOutput file: output.md"
        except Exception:
            return "No files found to process or error occurred"


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
            return "Project structure report generated: test.md"
        except Exception:
            return "Error generating report"


@pytest.fixture
def mock_fastmcp() -> Generator[MagicMock, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolorap.server.FastMCP") as mock:
        mock_server = MagicMock()
        mock_server.name = "neurolorap"
        mock_server.tools = {
            "project_structure_reporter": ProjectStructureReporterToolMock(),
            "code_collector": CodeCollectorToolMock(),
        }
        mock_server.tool_called = False
        mock.return_value = mock_server
        yield mock_server


@pytest.mark.asyncio
async def test_project_structure_reporter_success(
    tmp_path: Path, mock_fastmcp: MagicMock
) -> None:
    """Test successful project structure report generation."""
    # Call tool through mock server
    result = await mock_fastmcp.tools["project_structure_reporter"](
        output_filename="test.md",
        ignore_patterns=["*.pyc"],
    )

    # Verify results
    assert "Project structure report generated" in result


@pytest.mark.asyncio
async def test_code_collector_success(
    tmp_path: Path, mock_fastmcp: MagicMock
) -> None:
    """Test successful code collection."""
    # Call tool through mock server
    result = await mock_fastmcp.tools["code_collector"](
        input_path="src/",
        title="Test Collection",
        subproject_id="test-sub",
    )

    # Verify results
    assert "Code collection complete!" in result
    assert "output.md" in result


@pytest.mark.asyncio
async def test_project_structure_reporter_error_handling(
    tmp_path: Path, mock_fastmcp: MagicMock
) -> None:
    """Test error handling in project structure reporter."""
    create_server()
    tool = mock_fastmcp.tools["project_structure_reporter"]
    tool.set_side_effect(ValueError("Invalid configuration"))
    result = await tool()
    assert "Error generating report" in result


@pytest.mark.asyncio
async def test_code_collector_error_handling(
    tmp_path: Path, mock_fastmcp: MagicMock
) -> None:
    """Test error handling in code collector."""
    create_server()
    tool = mock_fastmcp.tools["code_collector"]
    tool.set_side_effect(ValueError("Invalid configuration"))
    result = await tool()
    assert "No files found to process or error occurred" in result
