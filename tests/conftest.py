"""Common test fixtures and configuration."""

from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for tests.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path: Path to temporary directory
    """
    yield tmp_path


@pytest.fixture
def project_root(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary project root directory.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Path to project root directory
    """
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    yield project_dir


@pytest.fixture
def sample_files(project_root: Path) -> Generator[list[Path], None, None]:
    """Create sample files for testing.

    Args:
        project_root: Project root directory fixture

    Returns:
        list[Path]: List of created file paths
    """
    # Create some sample files
    files = [
        project_root / "test.py",
        project_root / "test.js",
        project_root / "test.md",
        project_root / "src" / "main.py",
    ]

    # Create directories
    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)

    # Create files with some content
    for file in files:
        file.write_text(f"Test content in {file.name}")

    yield files

    # Cleanup
    for file in files:
        if file.exists():
            file.unlink()
        if file.parent != project_root and file.parent.exists():
            file.parent.rmdir()


@pytest.fixture
def ignore_file(project_root: Path) -> Generator[Path, None, None]:
    """Create a test .neuroloraignore file.

    Args:
        project_root: Project root directory fixture

    Returns:
        Path: Path to ignore file
    """
    ignore_path = project_root / ".neuroloraignore"
    ignore_content = """
# Test ignore patterns
*.log
node_modules/
__pycache__/
.git/
"""
    ignore_path.write_text(ignore_content)
    yield ignore_path

    if ignore_path.exists():
        ignore_path.unlink()
