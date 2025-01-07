"""Common test fixtures and configuration."""

import os
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

from mcpneurolora.log_utils import configure_test_logging
from mcpneurolora.server_utils import ensure_project_root_env


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator[None, None, None]:
    """Set up test environment variables."""
    # Store original env vars
    original_env = {
        "PROJECT_ROOT": os.environ.get("PROJECT_ROOT"),
        "AI_MODEL": os.environ.get("AI_MODEL"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
    }

    # Set test env vars
    os.environ["PROJECT_ROOT"] = os.path.dirname(os.path.dirname(__file__))
    os.environ["AI_MODEL"] = "test-model"
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    os.environ["GEMINI_API_KEY"] = "test-key"

    ensure_project_root_env()

    yield

    # Restore original env vars
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_env_config() -> Dict[str, Any]:
    """Mock environment configuration."""
    return {
        "PROJECT_ROOT": "/test/project/root",
        "AI_MODEL": "test-model",
        "OPENAI_API_KEY": "test-key",
        "ANTHROPIC_API_KEY": "test-key",
        "GEMINI_API_KEY": "test-key",
    }


@pytest.fixture
def project_env(tmp_path: Path) -> Path:
    """Create a temporary project environment for tests."""
    return tmp_path


@pytest.fixture(autouse=True)
def setup_test_logging() -> None:
    """Configure logging for tests.

    This fixture is automatically applied to all tests to ensure consistent
    and minimal logging output during test execution.
    """
    configure_test_logging()


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def ignore_file(project_env: Path) -> Path:
    """Create a temporary .neuroloraignore file."""
    ignore_file = project_env / ".neuroloraignore"
    ignore_file.write_text(
        """
*.log
node_modules/
__pycache__/
.git/
"""
    )
    return ignore_file


@pytest.fixture
def sample_files(project_env: Path) -> List[Path]:
    """Create sample files for testing."""
    files: List[Path] = []

    # Create test.py in root
    test_py = project_env / "test.py"
    test_py.write_text("Test content")
    files.append(test_py)

    # Create src/main.py
    src_dir = project_env / "src"
    src_dir.mkdir(exist_ok=True)
    main_py = src_dir / "main.py"
    main_py.write_text("Test content")
    files.append(main_py)

    return files


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as a slow test",
    )
