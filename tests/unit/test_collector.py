"""Unit tests for the CodeCollector class."""

import logging
import os
from pathlib import Path
from typing import Any

import pytest

from mcp_server_neurolorap.collector import CodeCollector, LanguageMap


def test_language_map() -> None:
    """Test LanguageMap extension to language mapping."""
    test_cases = [
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.ts", "typescript"),
        ("test.jsx", "jsx"),
        ("test.tsx", "tsx"),
        ("test.html", "html"),
        ("test.css", "css"),
        ("test.md", "markdown"),
        ("test.json", "json"),
        ("test.yml", "yaml"),
        ("test.yaml", "yaml"),
        ("test.sh", "bash"),
        ("test.unknown", ""),  # Unknown extension
        ("test", ""),  # No extension
        ("TEST.PY", "python"),  # Case insensitive
    ]

    for filename, expected_lang in test_cases:
        assert LanguageMap.get_language(Path(filename)) == expected_lang


def test_collect_files_with_spaces(project_root: Path) -> None:
    """Test collecting files with spaces in paths."""
    # Create test files
    space_dir = project_root / "test dir"
    space_dir.mkdir(exist_ok=True)
    space_file = space_dir / "test file.py"
    space_file.write_text("Test content")

    collector = CodeCollector(project_root)
    files = collector.collect_files(str(space_dir))

    assert space_file in files

    # Cleanup
    space_file.unlink()
    space_dir.rmdir()


def test_collect_files_absolute_path(project_root: Path) -> None:
    """Test collecting files with absolute paths."""
    test_file = project_root / "test.py"
    test_file.write_text("Test content")

    collector = CodeCollector(project_root)

    # Test with absolute path
    abs_path = test_file.absolute()
    files = collector.collect_files(str(abs_path))
    assert test_file in files

    # Test with path outside project root
    outside_dir = project_root.parent / "outside"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "test.py"
    outside_file.write_text("Test content")

    files = collector.collect_files(str(outside_file))
    assert outside_file in files

    # Cleanup
    test_file.unlink()
    outside_file.unlink()
    outside_dir.rmdir()


def test_read_file_content_encodings(project_root: Path) -> None:
    """Test reading files with different encodings."""
    collector = CodeCollector(project_root)

    # UTF-8 with BOM
    utf8_bom_file = project_root / "utf8_bom.txt"
    utf8_bom_file.write_bytes(b"\xef\xbb\xbfTest content")
    assert "Test content" in collector.read_file_content(utf8_bom_file)

    # UTF-16
    utf16_file = project_root / "utf16.txt"
    utf16_file.write_text("Test content", encoding="utf-16")
    assert "[Binary file content not shown]" == collector.read_file_content(
        utf16_file
    )

    # Invalid UTF-8
    invalid_file = project_root / "invalid.txt"
    invalid_file.write_bytes(b"Test content \xff\xff")
    assert "[Binary file content not shown]" == collector.read_file_content(
        invalid_file
    )

    # Cleanup
    utf8_bom_file.unlink()
    utf16_file.unlink()
    invalid_file.unlink()


def test_read_file_content_errors(project_root: Path) -> None:
    """Test error handling when reading files."""
    collector = CodeCollector(project_root)

    # Permission error
    no_access_file = project_root / "no_access.txt"
    no_access_file.write_text("Test content")
    os.chmod(no_access_file, 0o000)
    assert "[Permission denied]" == collector.read_file_content(no_access_file)
    os.chmod(no_access_file, 0o666)
    no_access_file.unlink()

    # File not found
    assert "[File not found]" == collector.read_file_content(
        project_root / "nonexistent.txt"
    )


def test_collect_code_output_files(project_root: Path) -> None:
    """Test creation of output files."""
    collector = CodeCollector(project_root)

    # Create test file
    test_file = project_root / "test.py"
    test_file.write_text("Test content")

    # Collect code
    output_path = collector.collect_code(str(test_file))
    assert output_path is not None
    assert output_path.exists()

    # Check content
    content = output_path.read_text()
    assert "# Code Collection" in content
    assert "## Table of Contents" in content
    assert "## Files" in content
    assert "### test.py" in content
    assert "```python" in content
    assert "Test content" in content

    # Check analysis prompt file
    analysis_path = output_path.parent / output_path.name.replace(
        "FULL_CODE_", "PROMPT_ANALYZE_"
    )
    assert analysis_path.exists()

    # Cleanup
    test_file.unlink()


def test_init_with_project_root(project_root: Path) -> None:
    """Test initializing CodeCollector with project root."""
    collector = CodeCollector(project_root)
    assert collector.project_root == project_root
    assert isinstance(collector.ignore_patterns, list)


def test_init_without_project_root() -> None:
    """Test initializing CodeCollector without project root."""
    collector = CodeCollector()
    assert collector.project_root == Path.cwd()


def test_load_ignore_patterns(project_root: Path, ignore_file: Path) -> None:
    """Test loading ignore patterns from .neuroloraignore file."""
    collector = CodeCollector(project_root)
    patterns = collector.load_ignore_patterns()
    assert "*.log" in patterns
    assert "node_modules/" in patterns
    assert "__pycache__/" in patterns
    assert ".git/" in patterns


def test_should_ignore_file(project_root: Path, ignore_file: Path) -> None:
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


def test_collect_files(project_root: Path, sample_files: list[Path]) -> None:
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


def test_collect_files_nonexistent(project_root: Path) -> None:
    """Test collecting files from nonexistent paths."""
    collector = CodeCollector(project_root)
    files = collector.collect_files("nonexistent")
    assert files == []


def test_read_file_content(
    project_root: Path, sample_files: list[Path]
) -> None:
    """Test reading file content."""
    collector = CodeCollector(project_root)

    # Test reading existing file
    content = collector.read_file_content(sample_files[0])
    assert content == f"Test content in {sample_files[0].name}"

    # Test reading nonexistent file
    content = collector.read_file_content(project_root / "nonexistent")
    assert content == "[File not found]"


def test_make_anchor() -> None:
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
    "title",
    ["Test Collection", "Project Files", "Source Code"],
    ids=["collection", "files", "source"],
)
def test_collect_code(
    project_root: Path, sample_files: list[Path], title: str
) -> None:
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


def test_collect_code_empty_input(project_root: Path) -> None:
    """Test code collection with empty input."""
    collector = CodeCollector(project_root)
    assert collector.collect_code("nonexistent") is None


@pytest.mark.parametrize(
    "error_type,error_msg,expected_log",
    [
        (ValueError, "Invalid input", "Invalid input"),
        (FileNotFoundError, "File not found", "File not found"),
        (PermissionError, "Permission denied", "Permission denied"),
        (Exception, "Unexpected error", "Unexpected error"),
    ],
    ids=[
        "value_error",
        "file_not_found",
        "permission_error",
        "unexpected_error",
    ],
)
def test_collect_code_error_handling(
    project_root: Path,
    caplog: pytest.LogCaptureFixture,
    error_type: type[Exception],
    error_msg: str,
    expected_log: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error handling during code collection."""
    collector = CodeCollector(project_root)

    def mock_collect_files(*args: Any, **kwargs: Any) -> list[Path]:
        raise error_type(error_msg)

    monkeypatch.setattr(collector, "collect_files", mock_collect_files)

    with caplog.at_level(logging.ERROR):
        result = collector.collect_code("test_input")
        assert result is None
        assert expected_log in caplog.text

        # Verify no output file was created
        output_files = list(project_root.glob("FULL_CODE_*"))
        assert len(output_files) == 0


def test_large_file_handling(project_root: Path) -> None:
    """Test handling of large files."""
    collector = CodeCollector(project_root)

    # Create a large file (>1MB)
    large_file = project_root / "large.txt"
    large_file.write_bytes(b"0" * (1024 * 1024 + 1))

    assert collector.should_ignore_file(large_file)

    # Cleanup
    large_file.unlink()


def test_binary_file_handling(project_root: Path) -> None:
    """Test handling of binary files."""
    collector = CodeCollector(project_root)

    # Create a binary file
    binary_file = project_root / "test.bin"
    binary_file.write_bytes(bytes(range(256)))

    content = collector.read_file_content(binary_file)
    assert content == "[Binary file content not shown]"

    # Cleanup
    binary_file.unlink()


def test_should_ignore_file_special_cases(project_root: Path) -> None:
    """Test special cases for file ignore logic."""
    collector = CodeCollector(project_root)

    # Test FULL_CODE_ files
    assert collector.should_ignore_file(project_root / "FULL_CODE_test.md")

    # Test .neuroloraignore file
    assert collector.should_ignore_file(project_root / ".neuroloraignore")

    # Test file with permission error
    no_access_file = project_root / "no_access.txt"
    no_access_file.write_text("Test content")
    os.chmod(no_access_file, 0o000)
    # On some systems, we might still be able to stat the file
    # even without read permissions. So we'll just verify that
    # should_ignore_file handles it correctly in either case
    try:
        no_access_file.stat()
        # If we can stat, we should still be able to check size
        assert collector.should_ignore_file(no_access_file) == (
            no_access_file.stat().st_size > 1024 * 1024
        )
    except PermissionError:
        # If we can't stat, it should be ignored
        assert collector.should_ignore_file(no_access_file)
    os.chmod(no_access_file, 0o666)
    no_access_file.unlink()

    # Test directory patterns
    assert collector.should_ignore_file(
        project_root / "node_modules" / "deep" / "test.js"
    )
    assert collector.should_ignore_file(project_root / "dist" / "index.html")

    # Test file outside project root
    outside_file = project_root.parent / "outside.py"
    outside_file.touch()
    assert not collector.should_ignore_file(outside_file)
    outside_file.unlink()


def test_collect_files_error_handling(project_root: Path) -> None:
    """Test error handling in collect_files."""
    collector = CodeCollector(project_root)

    # Test permission error
    no_access_dir = project_root / "no_access"
    no_access_dir.mkdir()
    no_access_file = no_access_dir / "test.py"
    no_access_file.write_text("Test content")
    os.chmod(no_access_dir, 0o000)

    files = collector.collect_files(str(no_access_dir))
    assert files == []

    os.chmod(no_access_dir, 0o777)
    no_access_file.unlink()
    no_access_dir.rmdir()

    # Test invalid path
    files = collector.collect_files("\0invalid")  # Invalid path character
    assert files == []  # Should return empty list for invalid paths

    # Test collecting from multiple paths with some failing
    test_file = project_root / "test.py"
    test_file.write_text("Test content")

    files = collector.collect_files(
        [str(test_file), "nonexistent", "\0invalid"]
    )
    assert len(files) == 1
    assert test_file in files

    test_file.unlink()


def test_collect_files_sorting(project_root: Path) -> None:
    """Test file sorting in collect_files."""
    collector = CodeCollector(project_root)

    # Create test files
    files = ["b.py", "a.py", "PROJECT_SUMMARY.md", "src/test.py", "README.md"]

    for file in files:
        path = project_root / file
        path.parent.mkdir(exist_ok=True)
        path.write_text("Test content")

    collected = collector.collect_files(str(project_root))

    # PROJECT_SUMMARY.md should be first
    assert collected[0].name == "PROJECT_SUMMARY.md"

    # Other files should be sorted alphabetically
    sorted_names = [f.name for f in collected[1:]]
    assert sorted_names == ["README.md", "a.py", "b.py", "test.py"]

    # Cleanup
    for file in files:
        path = project_root / file
        path.unlink()
        if path.parent != project_root:
            path.parent.rmdir()
