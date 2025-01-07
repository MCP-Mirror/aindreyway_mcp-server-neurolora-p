"""Unit tests for the BaseAnalyzer class."""

import logging
from pathlib import Path
from typing import Generator, List, Optional, Tuple, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest import mark

from mcpneurolora.file_naming import FileType
from mcpneurolora.tools.base_analyzer import BaseAnalyzer
from mcpneurolora.types import Context

# Disable logging for tests
logging.getLogger("mcpneurolora.tools.base_analyzer").setLevel(logging.CRITICAL)


class MockContextImpl:
    """Mock context implementation."""

    def __init__(self) -> None:
        """Initialize mock context."""
        self.info_calls: List[str] = []
        self.progress_calls: List[Tuple[float, Optional[float]]] = []

    def info(self, message: str, **extra: str) -> None:
        """Record info message."""
        self.info_calls.append(message)

    async def report_progress(
        self, progress: float, total: Optional[float] = None
    ) -> None:
        """Record progress update."""
        self.progress_calls.append((float(progress), total))


@pytest.fixture
def mock_context() -> MockContextImpl:
    """Create a mock context that implements Context protocol."""
    return MockContextImpl()


class MockProvider:
    """Mock AI provider for testing."""

    def __init__(self, name: str = "test_provider") -> None:
        """Initialize mock provider."""
        self.name = name
        self.analyze = AsyncMock(return_value="Test analysis result")


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


@pytest.fixture
def mock_create_provider() -> Generator[MockProvider, None, None]:
    """Mock AI provider creation."""
    with patch("mcpneurolora.tools.base_analyzer.create_provider") as mock:
        provider = MockProvider()
        mock.return_value = provider
        yield provider


@pytest.mark.asyncio
@mark.unit
async def test_analyzer_initialization(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test analyzer initialization."""
    # Test with project root
    analyzer = BaseAnalyzer(project_root=tmp_path)
    assert analyzer.project_root == tmp_path
    assert (
        analyzer.provider.name == mock_create_provider.name
    )  # Compare names instead of instances

    # Test without project root
    analyzer = BaseAnalyzer()
    assert analyzer.project_root == Path.cwd()


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_success(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
    mock_context: MockContextImpl,
) -> None:
    """Test successful code analysis."""
    # Setup
    analyzer = BaseAnalyzer(project_root=tmp_path, context=cast(Context, mock_context))

    # Test
    result = await analyzer.analyze_code(
        input_paths="test_input.py",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
        extra_content="Test content:",
    )

    # Verify
    assert result is not None
    assert result == Path("test_output.md")
    assert "Starting code collection..." in mock_context.info_calls
    assert "Code collected successfully" in mock_context.info_calls
    assert "Analysis complete!" in mock_context.info_calls
    assert (0.25, 100.0) in mock_context.progress_calls
    assert (0.50, 100.0) in mock_context.progress_calls
    assert (0.75, 100.0) in mock_context.progress_calls
    assert (1.0, 100.0) in mock_context.progress_calls


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_collection_failure(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of code collection failure."""
    # Setup
    mock_collector.collect_code = AsyncMock(return_value=None)
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test
    result = await analyzer.analyze_code(
        input_paths="test_input.py",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is None


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_provider_error(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of AI provider error."""
    # Setup
    mock_create_provider.analyze = AsyncMock(
        side_effect=RuntimeError("Analysis failed")
    )
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test
    result = await analyzer.analyze_code(
        input_paths="test_input.py",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is None


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_file_operations(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test file operations during analysis."""
    # Setup
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test
    result = await analyzer.analyze_code(
        input_paths="test_input.py",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is not None
    assert mock_async_io.read_file.call_count >= 2  # Code file and prompt
    assert mock_async_io.write_file.call_count >= 3  # Code, prompt, and result files


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_with_environment(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test analysis with environment variables."""
    # Setup
    monkeypatch.setenv("AI_MODEL", "test-model")
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test
    result = await analyzer.analyze_code(
        input_paths="test_input.py",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is not None
    # Check if model info is included in result
    write_calls = mock_async_io.write_file.call_args_list
    result_content = next(
        call[0][1] for call in write_calls if "Model: test-model" in call[0][1]
    )
    assert result_content is not None


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_with_multiple_paths(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test analysis with multiple input paths."""
    # Setup
    analyzer = BaseAnalyzer(project_root=tmp_path)
    input_paths = ["test1.py", "test2.py"]

    # Test
    result = await analyzer.analyze_code(
        input_paths=input_paths,
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is not None
    mock_collector.collect_code.assert_awaited_once_with(input_paths)


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_with_empty_analysis(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of empty analysis result."""
    # Setup
    mock_create_provider.analyze = AsyncMock(return_value="")
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test
    result = await analyzer.analyze_code(
        input_paths="test_input.py",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is not None  # Should still create output file


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_with_invalid_input(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of invalid input."""
    # Setup
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test with invalid input type
    mock_storage.get_output_path.return_value = None
    mock_collector.collect_code = AsyncMock(return_value=None)

    result = await analyzer.analyze_code(
        input_paths=123,  # type: ignore
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is None
    assert not mock_async_io.write_file.called


@pytest.mark.asyncio
@mark.unit
@mark.slow
async def test_analyze_code_with_empty_input(
    tmp_path: Path,
    mock_storage: MagicMock,
    mock_collector: MagicMock,
    mock_async_io: MagicMock,
    mock_create_provider: MockProvider,
) -> None:
    """Test handling of empty input."""
    # Setup
    analyzer = BaseAnalyzer(project_root=tmp_path)

    # Test with empty string
    result = await analyzer.analyze_code(
        input_paths="",
        title="Test Analysis",
        prompt_name="test",
        output_type=FileType.IMPROVE_RESULT,
    )

    # Verify
    assert result is None
