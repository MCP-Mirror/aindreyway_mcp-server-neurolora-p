"""Unit tests for the Improver class."""

import logging
import os
from pathlib import Path
from typing import Generator, List, Optional, Tuple, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcpneurolora.providers.base_provider import BaseProvider, Message, ProviderConfig
from mcpneurolora.tools.improver import Improver
from mcpneurolora.types import Context

# Disable logging for tests
logging.getLogger("mcpneurolora.tools.improver").setLevel(logging.CRITICAL)


class MockContext:
    """Mock context for testing."""

    def __init__(self) -> None:
        """Initialize mock context."""
        self.info_calls: List[str] = []
        self.progress_calls: List[Tuple[float, Optional[float]]] = []

    def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message: Message to log
        """
        self.info_calls.append(message)

    async def report_progress(
        self,
        progress: float,
        total: Optional[float] = None,
    ) -> None:
        """Report progress of an operation.

        Args:
            progress: Current progress value (0.0 to 1.0 or raw value)
            total: Optional total value for raw progress values
        """
        self.progress_calls.append((float(progress), total))


class MockProvider(BaseProvider):
    """Mock AI provider for testing."""

    name = "test_provider"

    def __init__(self) -> None:
        """Initialize mock provider."""
        config = ProviderConfig(
            api_key="test_key",
            model="test_model",
            timeout_ms=1000,
            extra_params={"token_limit": 1000},
        )
        super().__init__(config)
        self.mock_analyze = AsyncMock(
            return_value="1. [ ] ISSUE HIGH\nTest analysis result"
        )

    async def analyze(self, content: str) -> str:
        """Mock analyze method."""
        result = await self.mock_analyze(content)
        assert isinstance(result, str)
        return result

    def count_tokens(self, content: str) -> int:
        """Mock token counting."""
        return len(content) // 4

    async def _send_request(self, messages: List[Message]) -> str:
        """Mock request sending."""
        result = await self.mock_analyze(messages[0].content)
        assert isinstance(result, str)
        return result


@pytest.fixture
def mock_storage() -> Generator[MagicMock, None, None]:
    """Mock storage manager."""
    with patch("mcpneurolora.tools.base_analyzer.StorageManager") as mock:
        storage_instance = MagicMock()
        storage_instance.get_output_path.return_value = Path("test_output.md")
        mock.return_value = storage_instance
        yield storage_instance


@pytest.fixture
def mock_collector() -> Generator[MagicMock, None, None]:
    """Mock code collector."""
    with patch("mcpneurolora.tools.base_analyzer.Collector") as mock:
        collector_instance = MagicMock()
        collector_instance.collect_code = AsyncMock(
            return_value=Path("collected_code.md")
        )
        mock.return_value = collector_instance
        yield collector_instance


@pytest.fixture
def mock_async_io() -> Generator[MagicMock, None, None]:
    """Mock async IO operations."""
    with patch("mcpneurolora.tools.base_analyzer.async_io") as mock:
        mock.read_file = AsyncMock(return_value="Test file content")
        mock.write_file = AsyncMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_env() -> Generator[None, None, None]:
    """Mock environment variables."""
    with patch.dict(
        os.environ,
        {
            "AI_MODEL": "test_model",
            "OPENAI_API_KEY": "test_key",
            "AI_TIMEOUT_MS": "1000",
        },
        clear=True,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_create_provider(mock_env: None) -> Generator[MockProvider, None, None]:
    """Mock AI provider creation."""
    with patch("mcpneurolora.tools.base_analyzer.create_provider") as mock:
        provider = MockProvider()
        mock.return_value = provider
        yield provider


@pytest.mark.asyncio
async def test_improve_success(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
) -> None:
    """Test successful code improvement analysis."""
    # Setup
    mock_ctx = MockContext()
    improver = Improver(
        project_root=tmp_path,
        context=cast(Context, mock_ctx),
    )

    # Test
    result = await improver.improve("test_input.py")

    # Verify
    assert result is not None
    assert result == Path("test_output.md")
    assert "Starting code collection..." in mock_ctx.info_calls
    assert "Code collected successfully" in mock_ctx.info_calls
    assert "Analysis complete!" in mock_ctx.info_calls
    assert (1.0, 100.0) in mock_ctx.progress_calls


@pytest.mark.asyncio
async def test_improve_with_multiple_paths(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test code improvement with multiple input paths."""
    # Setup
    improver = Improver(project_root=tmp_path)
    input_paths = ["test1.py", "test2.py"]

    # Test
    result = await improver.improve(input_paths)

    # Verify
    assert result is not None
    assert result == Path("test_output.md")
    mock_collector.collect_code.assert_awaited_once_with(input_paths)


@pytest.mark.asyncio
async def test_improve_collection_failure(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of code collection failure."""
    # Setup
    mock_collector.collect_code = AsyncMock(return_value=None)
    improver = Improver(project_root=tmp_path)

    # Test
    result = await improver.improve("test_input.py")

    # Verify
    assert result is None


@pytest.mark.asyncio
async def test_improve_analysis_failure(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of analysis failure."""
    # Setup
    mock_create_provider.mock_analyze = AsyncMock(
        side_effect=RuntimeError("Analysis failed")
    )
    improver = Improver(project_root=tmp_path)

    # Test
    result = await improver.improve("test_input.py")

    # Verify
    assert result is None


@pytest.mark.asyncio
async def test_improve_with_context_reporting(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test progress reporting through context."""
    # Setup
    mock_ctx = MockContext()
    improver = Improver(
        project_root=tmp_path,
        context=cast(Context, mock_ctx),
    )

    # Test
    result = await improver.improve("test_input.py")

    # Verify
    assert result is not None
    assert len(mock_ctx.info_calls) > 0
    assert len(mock_ctx.progress_calls) > 0
    assert (0.25, 100.0) in mock_ctx.progress_calls
    assert (0.5, 100.0) in mock_ctx.progress_calls
    assert (0.75, 100.0) in mock_ctx.progress_calls
    assert (1.0, 100.0) in mock_ctx.progress_calls


@pytest.mark.asyncio
async def test_improve_file_operations(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test file operations during improvement process."""
    # Setup
    improver = Improver(project_root=tmp_path)

    # Test
    result = await improver.improve("test_input.py")

    # Verify
    assert result is not None
    # Check file reads
    assert mock_async_io.read_file.call_count >= 2  # Code file and prompt
    # Check file writes
    assert mock_async_io.write_file.call_count >= 3  # Code, prompt, and result files


@pytest.mark.asyncio
async def test_improve_without_project_root() -> None:
    """Test improver initialization without project root."""
    # Setup
    improver = Improver()

    # Verify
    assert improver.project_root == Path.cwd()


@pytest.mark.asyncio
async def test_improve_with_invalid_input(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of invalid input."""
    # Setup
    improver = Improver(project_root=tmp_path)

    # Test with invalid input type
    # We intentionally pass invalid type to test runtime type checking
    mock_storage.get_output_path.return_value = None
    mock_collector.collect_code = AsyncMock(return_value=None)

    result = await improver.improve(123)  # type: ignore[arg-type]

    # Verify
    assert result is None
    assert not mock_async_io.write_file.called


@pytest.mark.asyncio
async def test_improve_with_empty_input(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of empty input."""
    # Setup
    improver = Improver(project_root=tmp_path)

    # Test with empty string
    result = await improver.improve("")

    # Verify
    assert result is None


@pytest.mark.asyncio
async def test_improve_with_empty_analysis(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of empty analysis result."""
    # Setup
    mock_create_provider.mock_analyze = AsyncMock(return_value="")
    improver = Improver(project_root=tmp_path)

    # Test
    result = await improver.improve("test_input.py")

    # Verify
    assert result is not None
    assert result == Path("test_output.md")
