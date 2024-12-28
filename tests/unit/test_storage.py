"""Unit tests for the StorageManager class."""

import os
import shutil
from pathlib import Path

import pytest

from mcpneurolora.storage import StorageManager


@pytest.fixture
def storage_manager(project_root: Path) -> StorageManager:
    """Create a StorageManager instance for testing."""
    return StorageManager(project_root)


@pytest.fixture
def subproject_storage(project_root: Path) -> StorageManager:
    """Create a StorageManager instance with subproject."""
    return StorageManager(project_root, subproject_id="test-sub")


def test_init_basic(
    storage_manager: StorageManager, project_root: Path
) -> None:
    """Test basic initialization of StorageManager."""
    assert storage_manager.project_root == project_root
    assert storage_manager.project_name == project_root.name
    assert storage_manager.mcp_docs_dir == Path.home() / ".mcp-docs"
    assert (
        storage_manager.project_docs_dir
        == storage_manager.mcp_docs_dir / project_root.name
    )
    assert storage_manager.neurolora_link == project_root / ".neurolora"


def test_init_with_subproject(
    subproject_storage: StorageManager, project_root: Path
) -> None:
    """Test initialization with subproject ID."""
    expected_name = f"{project_root.name}-test-sub"
    assert subproject_storage.project_name == expected_name
    assert subproject_storage.project_docs_dir == (
        subproject_storage.mcp_docs_dir / expected_name
    )


def test_setup_creates_directories(storage_manager: StorageManager) -> None:
    """Test that setup creates all required directories."""
    storage_manager.setup()

    # Check main directories
    assert storage_manager.mcp_docs_dir.exists()
    assert storage_manager.project_docs_dir.exists()

    # Check initialization marker
    assert (storage_manager.project_docs_dir / ".initialized").exists()


def test_setup_creates_symlink(storage_manager: StorageManager) -> None:
    """Test that setup creates the .neurolora symlink correctly."""
    storage_manager.setup()

    # Check symlink exists and points to correct location
    assert storage_manager.neurolora_link.exists()
    assert storage_manager.neurolora_link.is_symlink()
    assert (
        storage_manager.neurolora_link.resolve()
        == storage_manager.project_docs_dir
    )


def test_setup_creates_task_files(storage_manager: StorageManager) -> None:
    """Test that setup creates TODO.md and DONE.md files."""
    storage_manager.setup()

    # Check task files exist
    assert (storage_manager.project_docs_dir / "TODO.md").exists()
    assert (storage_manager.project_docs_dir / "DONE.md").exists()


def test_setup_creates_ignore_file(storage_manager: StorageManager) -> None:
    """Test that setup creates .neuroloraignore file."""
    storage_manager.setup()

    # Check ignore file exists
    assert (storage_manager.project_root / ".neuroloraignore").exists()


def test_get_output_path(storage_manager: StorageManager) -> None:
    """Test getting output file path."""
    filename = "test.md"
    expected_path = storage_manager.project_docs_dir / filename
    assert storage_manager.get_output_path(filename) == expected_path


def test_symlink_update(
    storage_manager: StorageManager, project_root: Path
) -> None:
    """Test updating existing symlink."""
    # Create initial setup
    storage_manager.setup()

    # Create a different directory and update symlink
    new_target = project_root / "new_target"
    new_target.mkdir()

    # Update symlink
    storage_manager._create_or_update_symlink(
        storage_manager.neurolora_link, new_target, ".neurolora"
    )

    # Check symlink points to new target
    assert storage_manager.neurolora_link.resolve() == new_target

    # Cleanup
    new_target.rmdir()


def test_error_handling_invalid_symlink(
    storage_manager: StorageManager,
) -> None:
    """Test handling invalid symlink scenarios."""
    # Create a file instead of symlink
    storage_manager.neurolora_link.touch()

    # Setup should handle this by removing and recreating
    storage_manager.setup()

    assert storage_manager.neurolora_link.is_symlink()
    assert (
        storage_manager.neurolora_link.resolve()
        == storage_manager.project_docs_dir
    )


def test_error_handling_permission_denied(
    storage_manager: StorageManager,
) -> None:
    """Test handling permission denied errors."""
    if os.name != "nt":  # Skip on Windows
        # Make project directory read-only
        storage_manager.project_docs_dir.mkdir(parents=True, exist_ok=True)
        storage_manager.project_docs_dir.chmod(0o444)

        with pytest.raises(Exception) as exc_info:
            storage_manager._create_template_file(
                "todo.template.md", "TODO.md"
            )
        assert "Permission denied" in str(exc_info.value)

        # Cleanup
        storage_manager.project_docs_dir.chmod(0o777)


def test_template_file_missing_template(
    storage_manager: StorageManager, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling missing template files."""
    storage_manager.setup()

    storage_manager._create_template_file("nonexistent.template", "output.md")

    assert "Template file not found" in caplog.text


def test_cleanup_between_tests(storage_manager: StorageManager) -> None:
    """Test cleanup between tests."""
    storage_manager.setup()

    # Clean up test directories
    if storage_manager.project_docs_dir.exists():
        shutil.rmtree(storage_manager.project_docs_dir)
    if storage_manager.neurolora_link.exists():
        storage_manager.neurolora_link.unlink()

    assert not storage_manager.project_docs_dir.exists()
    assert not storage_manager.neurolora_link.exists()


@pytest.mark.parametrize(
    "subproject_id", ["test-sub", "feature-123", "debug-mode"]
)
def test_multiple_subprojects(project_root: Path, subproject_id: str) -> None:
    """Test handling multiple subprojects."""
    storage = StorageManager(project_root, subproject_id=subproject_id)
    storage.setup()

    expected_name = f"{project_root.name}-{subproject_id}"
    assert storage.project_name == expected_name
    assert storage.project_docs_dir.exists()
    assert storage.neurolora_link.exists()

    # Cleanup
    if storage.project_docs_dir.exists():
        shutil.rmtree(storage.project_docs_dir)
    if storage.neurolora_link.exists():
        storage.neurolora_link.unlink()


def test_concurrent_access(project_root: Path) -> None:
    """Test handling concurrent access to storage."""
    # Create multiple storage managers for same project
    storage1 = StorageManager(project_root)
    storage2 = StorageManager(project_root)

    # Setup both instances
    storage1.setup()
    storage2.setup()

    # Verify both instances work correctly
    assert storage1.project_docs_dir.exists()
    assert storage2.project_docs_dir.exists()
    assert storage1.neurolora_link.exists()
    assert storage2.neurolora_link.exists()

    # Verify they point to same location
    assert storage1.project_docs_dir == storage2.project_docs_dir
    assert (
        storage1.neurolora_link.resolve() == storage2.neurolora_link.resolve()
    )

    # Cleanup
    if storage1.project_docs_dir.exists():
        shutil.rmtree(storage1.project_docs_dir)
    if storage1.neurolora_link.exists():
        storage1.neurolora_link.unlink()
