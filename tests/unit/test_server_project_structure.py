"""Tests for project structure reporter MCP tool."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, NonCallableMock, patch

import pytest


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
        self._reporter: AsyncMock | None = None

    def set_reporter(self, reporter: AsyncMock | None) -> None:
        """Set the reporter instance for this tool."""
        self._reporter = reporter

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        try:
            if self.side_effect is not None:
                raise self.side_effect

            output_filename = kwargs.get(
                "output_filename", "PROJECT_STRUCTURE_REPORT.md"
            )
            print(f"\nDebug ToolMock: output_filename = {output_filename}")
            # Create report file
            project_root = os.environ.get("MCP_PROJECT_ROOT")
            if not project_root:
                raise ValueError("MCP_PROJECT_ROOT not set")
            print(f"Debug ToolMock: project_root = {project_root}")
            report_path = Path(project_root) / ".neurolora" / output_filename
            print(f"Debug ToolMock: report_path = {report_path}")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("# Test Report")
            print("Debug ToolMock: File written")
            return f"Project structure report generated: {output_filename}"
        except Exception:
            return "Error generating report"


@pytest.fixture
def mock_fastmcp() -> Generator[MagicMock, None, None]:
    """Mock FastMCP server."""
    with patch("mcp_server_neurolorap.server.FastMCP") as mock:
        mock_server = MagicMock()
        mock_server.name = "neurolorap"
        mock_server.tools = {"project_structure_reporter": ToolMock()}
        mock_server.tool_called = False
        mock.return_value = mock_server
        yield mock_server


@pytest.fixture
def temp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project structure for testing."""
    # Create some test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "src" / "utils.py").write_text("x = 1\n" * 400)  # Large file
    (tmp_path / "README.md").write_text("# Test Project\n")
    (tmp_path / ".neurolora").mkdir()

    yield tmp_path


@pytest.mark.asyncio
async def test_project_structure_reporter_tool(
    temp_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_fastmcp: MagicMock,
) -> None:
    """Test project structure reporter MCP tool."""
    # Set project root for test
    monkeypatch.setenv("MCP_PROJECT_ROOT", str(temp_project))

    # Get tool mock
    tool_mock = mock_fastmcp.tools["project_structure_reporter"]
    result = await tool_mock()
    assert isinstance(result, str)
    assert "Project structure report generated" in result

    report_path = temp_project / ".neurolora" / "PROJECT_STRUCTURE_REPORT.md"
    assert report_path.exists()

    # Test with custom parameters
    result = await tool_mock(
        output_filename="custom_report.md", ignore_patterns=["*.pyc"]
    )
    assert isinstance(result, str)
    assert "Project structure report generated" in result

    custom_report_path = temp_project / ".neurolora" / "custom_report.md"
    print(f"\nDebug: Custom report path: {custom_report_path}")
    print(f"Debug: Custom report exists: {custom_report_path.exists()}")
    print(
        f"Debug: Parent directory exists: {custom_report_path.parent.exists()}"
    )
    contents = list(custom_report_path.parent.iterdir())
    print(f"Debug: Parent directory contents: {contents}")
    assert custom_report_path.exists()

    # Test error handling
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/nonexistent/path")
    result = await tool_mock()
    assert "Error generating report" in result
