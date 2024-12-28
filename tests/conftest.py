"""Common test fixtures and configuration."""

from pathlib import Path
from typing import Generator, List

import pytest


def create_test_files(root: Path, files: List[str]) -> List[Path]:
    """Create test files with content.

    Args:
        root: Root directory for files
        files: List of file paths relative to root

    Returns:
        List[Path]: List of created file paths
    """
    paths = [root / file for file in files]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Test content in {path.name}")
    return paths


def cleanup_test_files(files: List[Path], root: Path) -> None:
    """Clean up test files and empty directories.

    Args:
        files: List of file paths to clean up
        root: Root directory to preserve
    """
    for file in files:
        if file.exists():
            file.unlink()
        current = file.parent
        while current != root and current.exists():
            if not any(current.iterdir()):
                current.rmdir()
            current = current.parent


@pytest.fixture  # type: ignore
def project_env(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project environment.

    Creates a project directory within the temporary path.
    This replaces both temp_dir and project_root fixtures.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path: Path to project directory
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    yield project_dir


@pytest.fixture  # type: ignore
def sample_files(project_env: Path) -> Generator[List[Path], None, None]:
    """Create sample files for testing.

    Uses project_env instead of project_root and supports customizable
    file list.

    Args:
        project_env: Project environment fixture

    Returns:
        List[Path]: List of created file paths
    """
    test_files = ["test.py", "test.js", "test.md", "src/main.py"]

    paths = create_test_files(project_env, test_files)
    yield paths
    cleanup_test_files(paths, project_env)


@pytest.fixture  # type: ignore
def ignore_file(project_env: Path) -> Generator[Path, None, None]:
    """Create a test .neuroloraignore file.

    Args:
        project_env: Project environment fixture

    Returns:
        Path: Path to ignore file
    """
    ignore_path = project_env / ".neuroloraignore"
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
