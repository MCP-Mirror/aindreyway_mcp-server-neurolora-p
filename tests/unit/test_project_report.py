"""Tests for project structure reporter module."""

import os
from pathlib import Path
from typing import Generator

import pytest

from mcpneurolora.tools.reporter import Reporter
from mcpneurolora.utils import async_io


@pytest.fixture
def temp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project structure for testing."""
    # Create some test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "src" / "utils.py").write_text("x = 1\n" * 400)  # Large file
    (tmp_path / "README.md").write_text("# Test Project\n")
    (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\x03")

    yield tmp_path


@pytest.mark.asyncio
async def test_should_ignore(temp_project: Path) -> None:
    """Test file/directory ignore patterns."""
    reporter = Reporter(
        root_dir=temp_project,
        ignore_patterns=["*.bin", "*.pyc"],
    )

    assert await reporter.should_ignore(temp_project / "binary.bin")
    assert await reporter.should_ignore(temp_project / "cache.pyc")
    assert not await reporter.should_ignore(temp_project / "src" / "main.py")


@pytest.mark.asyncio
async def test_analyze_file(temp_project: Path) -> None:
    """Test file analysis functionality."""
    reporter = Reporter(root_dir=temp_project)

    # Test normal file
    main_data = await reporter.analyze_file(temp_project / "src" / "main.py")
    assert main_data["path"] == os.path.join("src", "main.py")
    assert main_data["lines"] == 2
    assert not main_data["is_large"]
    assert not main_data["is_complex"]
    assert not main_data["error"]

    # Test large file
    utils_data = await reporter.analyze_file(temp_project / "src" / "utils.py")
    assert utils_data["path"] == os.path.join("src", "utils.py")
    assert utils_data["lines"] == 400
    assert not utils_data["is_large"]  # Not large by size
    assert utils_data["is_complex"]  # Large by lines
    assert not utils_data["error"]

    # Test binary file
    binary_data = await reporter.analyze_file(temp_project / "binary.bin")
    assert binary_data["path"] == "binary.bin"
    assert binary_data["lines"] == 0
    assert not binary_data["is_large"]
    assert not binary_data["is_complex"]
    assert not binary_data["error"]


@pytest.mark.asyncio
async def test_analyze_project_structure(temp_project: Path) -> None:
    """Test project structure analysis."""
    reporter = Reporter(
        root_dir=temp_project,
        ignore_patterns=["*.bin"],
    )

    report_data = await reporter.analyze_project_structure()

    assert len(report_data["files"]) == 3  # main.py, utils.py, README.md
    assert report_data["total_lines"] > 0
    assert report_data["total_tokens"] > 0
    assert report_data["large_files"] == 0
    assert report_data["error_files"] == 0


@pytest.mark.asyncio
async def test_generate_report(temp_project: Path) -> None:
    """Test markdown report generation."""
    reporter = Reporter(root_dir=temp_project)
    output_path = await reporter.generate_report()

    assert output_path is not None
    assert output_path.exists()
    content = await async_io.read_file(output_path)
    assert "# Project Structure Report" in content
    assert "## Project Tree" in content
    assert "## Summary" in content
    assert "## Notes" in content
