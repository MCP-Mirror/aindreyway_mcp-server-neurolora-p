"""Tests for tools/executor.py module."""

from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp import Context

from mcpneurolora.tools.executor import ToolExecutor
from mcpneurolora.utils.progress import ProgressTracker


@pytest.fixture
def mock_context() -> Context:
    """Create mock MCP context."""
    return MagicMock(spec=Context)


@pytest.fixture
def mock_progress() -> Generator[MagicMock, None, None]:
    """Mock progress tracker."""
    with patch("mcpneurolora.tools.executor.ProgressTracker") as mock:
        progress = MagicMock(spec=ProgressTracker)
        mock.return_value = progress
        progress.start = AsyncMock()
        progress.stop = AsyncMock()
        yield progress


@pytest.fixture
def executor(mock_context: Context) -> ToolExecutor:
    """Create ToolExecutor instance."""
    return ToolExecutor(project_root="/test/path", context=mock_context)


@pytest.mark.asyncio
async def test_execute_code_collector_success(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test successful code collection."""
    mock_collector = AsyncMock()
    mock_collector.collect_code.return_value = Path("/test/output.md")

    with patch("mcpneurolora.tools.executor.Collector", return_value=mock_collector):
        result = await executor.execute_code_collector("test/path")
        assert result == "/test/output.md"
        assert mock_collector.collect_code.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Collection complete")


@pytest.mark.asyncio
async def test_execute_code_collector_no_files(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test code collection with no files."""
    mock_collector = AsyncMock()
    mock_collector.collect_code.return_value = None

    with patch("mcpneurolora.tools.executor.Collector", return_value=mock_collector):
        result = await executor.execute_code_collector("test/path")
        assert result == "No files found to process"
        assert mock_collector.collect_code.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Error: Collection failed")


@pytest.mark.asyncio
async def test_execute_code_collector_error(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test code collection with error."""
    mock_collector = AsyncMock()
    mock_collector.collect_code.side_effect = Exception("Test error")

    with patch("mcpneurolora.tools.executor.Collector", return_value=mock_collector):
        result = await executor.execute_code_collector("test/path")
        assert result == "Error during code collection: Test error"
        assert mock_collector.collect_code.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Error: Collection failed")


@pytest.mark.asyncio
async def test_execute_project_structure_reporter_success(
    executor: ToolExecutor,
) -> None:
    """Test successful project structure report generation."""
    mock_reporter = AsyncMock()
    mock_reporter.analyze_project_structure.return_value = {"test": "data"}

    with patch(
        "mcpneurolora.tools.executor.Reporter", return_value=mock_reporter
    ), patch("mcpneurolora.tools.executor.async_io.ensure_dir") as mock_ensure_dir:
        result = await executor.execute_project_structure_reporter("test.md")
        assert result == "/test/path/.neurolora/test.md"
        assert mock_reporter.analyze_project_structure.called
        assert mock_reporter.generate_markdown_report.called
        assert mock_ensure_dir.called


@pytest.mark.asyncio
async def test_execute_project_structure_reporter_error(executor: ToolExecutor) -> None:
    """Test project structure report generation with error."""
    mock_reporter = AsyncMock()
    mock_reporter.analyze_project_structure.side_effect = Exception("Test error")

    with patch(
        "mcpneurolora.tools.executor.Reporter", return_value=mock_reporter
    ), patch("mcpneurolora.tools.executor.async_io.ensure_dir") as mock_ensure_dir:
        mock_ensure_dir.return_value = True
        result = await executor.execute_project_structure_reporter("test.md")
        assert result == "Error during report generation: Test error"
        assert mock_reporter.analyze_project_structure.called


@pytest.mark.asyncio
async def test_execute_improve_success(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test successful code improvement."""
    mock_improver = AsyncMock()
    mock_improver.improve.return_value = Path("/test/output.md")

    with patch("mcpneurolora.tools.executor.Improver", return_value=mock_improver):
        result = await executor.execute_improve("test/path")
        assert result == "/test/output.md"
        assert mock_improver.improve.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Analysis complete")


@pytest.mark.asyncio
async def test_execute_improve_failure(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test code improvement with failure."""
    mock_improver = AsyncMock()
    mock_improver.improve.return_value = None

    with patch("mcpneurolora.tools.executor.Improver", return_value=mock_improver):
        result = await executor.execute_improve("test/path")
        assert result == "Failed to analyze code"
        assert mock_improver.improve.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Error: Analysis failed")


@pytest.mark.asyncio
async def test_execute_improve_error(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test code improvement with error."""
    mock_improver = AsyncMock()
    mock_improver.improve.side_effect = Exception("Test error")

    with patch("mcpneurolora.tools.executor.Improver", return_value=mock_improver):
        result = await executor.execute_improve("test/path")
        assert result == "Error during code analysis: Test error"
        assert mock_improver.improve.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Error: Analysis failed")


@pytest.mark.asyncio
async def test_execute_request_success(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test successful request execution."""
    mock_requester = AsyncMock()
    mock_requester.request.return_value = Path("/test/output.md")

    with patch("mcpneurolora.tools.executor.Requester", return_value=mock_requester):
        result = await executor.execute_request("test/path", "test request")
        assert result == "/test/output.md"
        assert mock_requester.request.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Analysis complete")


@pytest.mark.asyncio
async def test_execute_request_no_text(executor: ToolExecutor) -> None:
    """Test request execution with no request text."""
    result = await executor.execute_request("test/path", "")
    assert result == "Request text is required"


@pytest.mark.asyncio
async def test_execute_request_failure(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test request execution with failure."""
    mock_requester = AsyncMock()
    mock_requester.request.return_value = None

    with patch("mcpneurolora.tools.executor.Requester", return_value=mock_requester):
        result = await executor.execute_request("test/path", "test request")
        assert result == "Failed to process request"
        assert mock_requester.request.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Error: Analysis failed")


@pytest.mark.asyncio
async def test_execute_request_error(
    executor: ToolExecutor, mock_progress: MagicMock
) -> None:
    """Test request execution with error."""
    mock_requester = AsyncMock()
    mock_requester.request.side_effect = Exception("Test error")

    with patch("mcpneurolora.tools.executor.Requester", return_value=mock_requester):
        result = await executor.execute_request("test/path", "test request")
        assert result == "Error during request analysis: Test error"
        assert mock_requester.request.called
        assert mock_progress.start.called
        assert mock_progress.stop.called
        mock_progress.stop.assert_called_with("Error: Analysis failed")


def test_format_result(executor: ToolExecutor) -> None:
    """Test result formatting."""
    result = executor.format_result("test result")
    assert isinstance(result, dict)
    assert result["result"] == "test result"


def test_executor_init_default() -> None:
    """Test executor initialization with defaults."""
    executor = ToolExecutor()
    assert executor.project_root == Path.cwd()
    assert executor.context is None


def test_executor_init_with_path() -> None:
    """Test executor initialization with path."""
    executor = ToolExecutor(project_root="/test/path")
    assert executor.project_root == Path("/test/path")
    assert executor.context is None


def test_executor_init_with_context(mock_context: Context) -> None:
    """Test executor initialization with context."""
    executor = ToolExecutor(context=mock_context)
    assert executor.project_root == Path.cwd()
    assert executor.context == mock_context
