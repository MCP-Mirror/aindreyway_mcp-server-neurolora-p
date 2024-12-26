"""Tests for project structure reporter MCP tool."""

from pathlib import Path
from typing import Generator

import pytest

from mcp_server_neurolorap.server import create_server


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
    temp_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test project structure reporter MCP tool."""
    # Set project root for test
    monkeypatch.setenv("MCP_PROJECT_ROOT", str(temp_project))

    # Create server instance
    server = create_server()

    # Test with default parameters
    result = await server.tools["project_structure_reporter"]()
    assert isinstance(result, str)
    assert "Project structure report generated" in result

    report_path = temp_project / ".neurolora" / "PROJECT_STRUCTURE_REPORT.md"
    assert report_path.exists()

    # Test with custom parameters
    result = await server.tools["project_structure_reporter"](
        output_filename="custom_report.md",
        ignore_patterns=["*.pyc"],
    )
    assert isinstance(result, str)
    assert "Project structure report generated" in result

    custom_report_path = temp_project / ".neurolora" / "custom_report.md"
    assert custom_report_path.exists()

    # Test error handling
    monkeypatch.setenv("MCP_PROJECT_ROOT", "/nonexistent/path")
    result = await server.tools["project_structure_reporter"]()
    assert "Error generating report" in result
