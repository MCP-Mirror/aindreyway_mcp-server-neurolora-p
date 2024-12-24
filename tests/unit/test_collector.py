"""Unit tests for the CodeCollector class."""

import logging
from pathlib import Path
import pytest
from mcp_server_neurolorap.collector import CodeCollector, LanguageMap


def test_init_with_project_root(project_root: Path):
    """Test initializing CodeCollector with project root."""
    collector = CodeCollector(project_root)
    assert collector.project_root == project_root
    assert isinstance(collector.ignore_patterns, list)


def test_init_without_project_root():
    """Test initializing CodeCollector without project root."""
    collector = CodeCollector()
    assert collector.project_root == Path.cwd()


def test_load_ignore_patterns(project_root: Path, ignore_file: Path):
    """Test loading ignore patterns from .neuroloraignore file."""
    collector = CodeCollector(project_root)
    patterns = collector.load_ignore_patterns()
    assert "*.log" in patterns
    assert "node_modules/" in patterns
    assert "__pycache__/" in patterns
    assert ".git/" in patterns


def test_should_ignore_file(project_root: Path, ignore_file: Path):
    """Test file ignore logic."""
    collector = CodeCollector(project_root)

    # Should ignore files matching patterns
    assert collector.should_ignore_file(project_root / "test.log")
    assert collector.should_ignore_file(
        project_root / "node_modules" / "test.js"
    )
    assert collector.should_ignore_file(
        project_root / "__pycache__" / "test.pyc"
    )
    assert collector.should_ignore_file(project_root / ".git" / "config")

    # Should not ignore regular files
    assert not collector.should_ignore_file(project_root / "test.py")
    assert not collector.should_ignore_file(project_root / "src" / "main.py")


def test_collect_files(project_root: Path, sample_files: list[Path]):
    """Test collecting files from input paths."""
    collector = CodeCollector(project_root)

    # Test collecting single file
    files = collector.collect_files(str(sample_files[0]))
    assert len(files) == 1
    assert files[0] == sample_files[0]

    # Test collecting directory
    files = collector.collect_files(str(project_root))
    assert len(files) == len(sample_files)
    assert all(f in files for f in sample_files)

    # Test collecting multiple paths
    paths = [str(sample_files[0]), str(project_root / "src")]
    files = collector.collect_files(paths)
    assert len(files) == 2
    assert sample_files[0] in files
    assert project_root / "src" / "main.py" in files


def test_collect_files_nonexistent(project_root: Path):
    """Test collecting files from nonexistent paths."""
    collector = CodeCollector(project_root)
    files = collector.collect_files("nonexistent")
    assert files == []


def test_read_file_content(project_root: Path, sample_files: list[Path]):
    """Test reading file content."""
    collector = CodeCollector(project_root)

    # Test reading existing file
    content = collector.read_file_content(sample_files[0])
    assert content == f"Test content in {sample_files[0].name}"

    # Test reading nonexistent file
    content = collector.read_file_content(project_root / "nonexistent")
    assert content == "[File not found]"


def test_make_anchor():
    """Test markdown anchor generation."""
    collector = CodeCollector()

    test_cases = [
        ("src/test.py", "src-test-py"),
        ("test file.js", "test-file-js"),
        ("TEST.PY", "test-py"),
        ("src/sub/test.py", "src-sub-test-py"),
    ]

    for path, expected in test_cases:
        assert collector.make_anchor(Path(path)) == expected


@pytest.mark.parametrize(
    "title", ["Test Collection", "Project Files", "Source Code"]
)
def test_collect_code(
    project_root: Path, sample_files: list[Path], title: str
):
    """Test full code collection process."""
    collector = CodeCollector(project_root)

    # Test collecting all files
    output_path = collector.collect_code(str(project_root), title=title)
    assert output_path is not None
    assert output_path.exists()

    # Verify output file content
    content = output_path.read_text()

    # Check title
    assert f"# {title}" in content

    # Check table of contents
    assert "## Table of Contents" in content
    for file in sample_files:
        rel_path = file.relative_to(project_root)
        assert f"- [{rel_path}]" in content

    # Check file contents
    assert "## Files" in content
    for file in sample_files:
        rel_path = file.relative_to(project_root)
        assert f"### {rel_path}" in content
        lang = LanguageMap.get_language(file)
        assert f"```{lang}" in content
        assert f"Test content in {file.name}" in content


def test_collect_code_empty_input(project_root: Path):
    """Test code collection with empty input."""
    collector = CodeCollector(project_root)
    assert collector.collect_code("nonexistent") is None


def test_collect_code_error_handling(project_root: Path, caplog):
    """Test error handling during code collection."""
    collector = CodeCollector(project_root)

    with caplog.at_level(logging.ERROR):
        # Test with invalid input
        assert collector.collect_code(None) is None  # type: ignore
        assert "Unexpected error" in caplog.text

        # Test with permission error
        test_file = project_root / "test.py"
        test_file.touch(mode=0o000)  # Make file unreadable
        assert collector.collect_code(str(test_file)) is None
        assert "Permission denied" in caplog.text

        # Cleanup
        test_file.chmod(0o666)
        test_file.unlink()


def test_large_file_handling(project_root: Path):
    """Test handling of large files."""
    collector = CodeCollector(project_root)

    # Create a large file (>1MB)
    large_file = project_root / "large.txt"
    large_file.write_bytes(b"0" * (1024 * 1024 + 1))

    assert collector.should_ignore_file(large_file)

    # Cleanup
    large_file.unlink()


def test_binary_file_handling(project_root: Path):
    """Test handling of binary files."""
    collector = CodeCollector(project_root)

    # Create a binary file
    binary_file = project_root / "test.bin"
    binary_file.write_bytes(bytes(range(256)))

    content = collector.read_file_content(binary_file)
    assert content == "[Binary file content not shown]"

    # Cleanup
    binary_file.unlink()
