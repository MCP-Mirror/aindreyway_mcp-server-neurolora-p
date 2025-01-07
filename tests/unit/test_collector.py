"""Unit tests for the Collector class."""

import os
from pathlib import Path
from typing import Any, List

import pytest

from mcpneurolora.tools.collector import Collector, LanguageMap
from mcpneurolora.utils import async_io


def test_language_map() -> None:
    """Test LanguageMap extension to language mapping."""
    test_cases = [
        # Web technologies
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.ts", "typescript"),
        ("test.jsx", "jsx"),
        ("test.tsx", "tsx"),
        ("test.html", "html"),
        ("test.css", "css"),
        ("test.scss", "scss"),
        ("test.sass", "sass"),
        ("test.less", "less"),
        # Documentation and config
        ("test.md", "markdown"),
        ("test.json", "json"),
        ("test.yml", "yaml"),
        ("test.yaml", "yaml"),
        ("test.toml", "toml"),
        ("test.ini", "ini"),
        ("test.conf", "conf"),
        # Shell scripts
        ("test.sh", "bash"),
        ("test.bash", "bash"),
        ("test.zsh", "bash"),
        ("test.bat", "batch"),
        ("test.ps1", "powershell"),
        # Programming languages
        ("test.java", "java"),
        ("test.cpp", "cpp"),
        ("test.hpp", "cpp"),
        ("test.c", "c"),
        ("test.h", "c"),
        ("test.rs", "rust"),
        ("test.go", "go"),
        ("test.rb", "ruby"),
        ("test.php", "php"),
        ("test.swift", "swift"),
        ("test.kt", "kotlin"),
        ("test.kts", "kotlin"),
        ("test.r", "r"),
        ("test.lua", "lua"),
        ("test.m", "matlab"),
        ("test.pl", "perl"),
        ("test.xml", "xml"),
        # Special cases
        ("test.unknown", ""),  # Unknown extension
        ("test", ""),  # No extension
        ("TEST.PY", "python"),  # Case insensitive
    ]

    for filename, expected_lang in test_cases:
        assert LanguageMap.get_language(Path(filename)) == expected_lang


@pytest.mark.asyncio
async def test_collect_files_with_spaces(project_env: Path) -> None:
    """Test collecting files with spaces in paths."""
    # Create test files
    space_dir = project_env / "test dir"
    space_dir.mkdir(exist_ok=True)
    space_file = space_dir / "test file.py"
    space_file.write_text("Test content")

    collector = Collector(project_env)
    files = await collector.collect_files(str(space_dir))

    assert space_file in files

    # Cleanup
    space_file.unlink()
    space_dir.rmdir()


@pytest.mark.asyncio
async def test_collect_files_absolute_path(project_env: Path) -> None:
    """Test collecting files with absolute paths."""
    test_file = project_env / "test.py"
    test_file.write_text("Test content")

    collector = Collector(project_env)

    # Test with absolute path
    abs_path = test_file.absolute()
    files = await collector.collect_files(str(abs_path))
    assert test_file in files

    # Test with path outside project root
    outside_dir = project_env.parent / "outside"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "test.py"
    outside_file.write_text("Test content")

    files = await collector.collect_files(str(outside_file))
    assert outside_file in files

    # Cleanup
    test_file.unlink()
    outside_file.unlink()
    outside_dir.rmdir()


@pytest.mark.asyncio
async def test_should_ignore_file(project_env: Path, ignore_file: Path) -> None:
    """Test file ignore logic."""
    collector = Collector(project_env)
    collector.ignore_patterns = await collector.load_ignore_patterns()

    # Create test files with proper permissions
    test_py = project_env / "test.py"
    test_py.write_text("Test content")
    os.chmod(test_py, 0o644)  # Ensure readable

    src_dir = project_env / "src"
    src_dir.mkdir(exist_ok=True)
    main_py = src_dir / "main.py"
    main_py.write_text("Test content")
    os.chmod(main_py, 0o644)  # Ensure readable

    try:
        # Should ignore files matching patterns
        assert await collector.should_ignore_file(project_env / "test.log")
        assert await collector.should_ignore_file(
            project_env / "node_modules" / "test.js"
        )
        assert await collector.should_ignore_file(
            project_env / "__pycache__" / "test.pyc"
        )
        assert await collector.should_ignore_file(project_env / ".git" / "config")

        # Should not ignore regular files
        assert not await collector.should_ignore_file(test_py)
        assert not await collector.should_ignore_file(main_py)
    finally:
        # Cleanup
        test_py.unlink()
        main_py.unlink()
        src_dir.rmdir()


@pytest.mark.asyncio
async def test_collect_files(project_env: Path, sample_files: List[Path]) -> None:
    """Test collecting files from input paths."""
    collector = Collector(project_env)

    # Test collecting single file
    files = await collector.collect_files(str(sample_files[0]))
    assert len(files) == 1
    assert files[0] == sample_files[0]

    # Test collecting directory
    files = await collector.collect_files(str(project_env))
    assert len(files) == len(sample_files)
    assert all(f in files for f in sample_files)

    # Test collecting multiple paths
    paths = [str(sample_files[0]), str(project_env / "src")]
    files = await collector.collect_files(paths)
    assert len(files) == 2
    assert sample_files[0] in files
    assert project_env / "src" / "main.py" in files


@pytest.mark.asyncio
async def test_collect_files_nonexistent(project_env: Path) -> None:
    """Test collecting files from nonexistent paths."""
    collector = Collector(project_env)
    files = await collector.collect_files("nonexistent")
    assert files == []


@pytest.mark.asyncio
async def test_collect_code_output_files(project_env: Path) -> None:
    """Test creation of output files and token counting."""
    collector = Collector(project_env)

    # Create test file with known content length
    test_file = project_env / "test.py"
    content = "x" * 100  # Should be approximately 25 tokens (4 chars per token)
    test_file.write_text(content)

    # Collect code
    output_path = await collector.collect_code(str(test_file))
    assert output_path is not None

    # Check content
    file_content = await async_io.read_file(output_path)
    assert "# Code Collection" in file_content
    assert "## Table of Contents" in file_content
    assert "## Files" in file_content
    assert "### test.py" in file_content
    assert "```python" in file_content
    assert content in file_content

    # Check token count (should be at least the content length / 4)
    # Plus some overhead for markdown formatting
    assert len(file_content) // 4 >= 25

    # Check analysis prompt file
    analysis_path = output_path.parent / output_path.name.replace(
        "FULL_CODE_", "PROMPT_ANALYZE_"
    )
    assert await async_io.path_exists(analysis_path)

    # Cleanup
    test_file.unlink()


def test_init_with_project_root(project_env: Path) -> None:
    """Test initializing Collector with project root."""
    collector = Collector(project_env)
    assert collector.project_root == project_env
    assert isinstance(collector.ignore_patterns, list)


def test_init_without_project_root() -> None:
    """Test initializing Collector without project root."""
    collector = Collector()
    assert collector.project_root == Path.cwd()


@pytest.mark.asyncio
async def test_load_ignore_patterns(project_env: Path, ignore_file: Path) -> None:
    """Test loading ignore patterns from .neuroloraignore file."""
    collector = Collector(project_env)
    patterns = await collector.load_ignore_patterns()
    assert "*.log" in patterns
    assert "node_modules/" in patterns
    assert "__pycache__/" in patterns
    assert ".git/" in patterns


def test_make_anchor() -> None:
    """Test markdown anchor generation."""
    collector = Collector()

    test_cases = [
        ("src/test.py", "src-test-py"),
        ("test file.js", "test-file-js"),
        ("TEST.PY", "test-py"),
        ("src/sub/test.py", "src-sub-test-py"),
    ]

    for path, expected in test_cases:
        assert collector.make_anchor(Path(path)) == expected


@pytest.mark.asyncio
async def test_collect_code_empty_input(project_env: Path) -> None:
    """Test code collection with empty input."""
    collector = Collector(project_env)
    assert await collector.collect_code("nonexistent") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type,error_msg,expected_log",
    [
        (
            ValueError,
            "Invalid input",
            "Invalid input error during code collection",
        ),
        (
            FileNotFoundError,
            "File not found",
            "System error during code collection",
        ),
        (
            PermissionError,
            "Permission denied",
            "System error during code collection",
        ),
        (
            Exception,
            "Unexpected error",
            "Runtime error during code collection",
        ),
    ],
)
async def test_collect_code_error_handling(
    project_env: Path,
    caplog: pytest.LogCaptureFixture,
    error_type: type[Exception],
    error_msg: str,
    expected_log: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error handling during code collection."""
    collector = Collector(project_env)

    async def mock_collect_files(*args: Any, **kwargs: Any) -> List[Path]:
        raise error_type(error_msg)

    monkeypatch.setattr(collector, "collect_files", mock_collect_files)

    result = await collector.collect_code("test_input")
    assert result is None


@pytest.mark.asyncio
async def test_large_file_handling(project_env: Path) -> None:
    """Test handling of large files."""
    collector = Collector(project_env)

    # Create a large file (>1MB)
    large_file = project_env / "large.txt"
    large_file.write_bytes(b"0" * (1024 * 1024 + 1))

    assert await collector.should_ignore_file(large_file)

    # Cleanup
    large_file.unlink()


@pytest.mark.asyncio
async def test_binary_file_handling(project_env: Path) -> None:
    """Test handling of binary files and high ASCII characters."""
    collector = Collector(project_env)

    # Test file with null bytes
    binary_file = project_env / "test.bin"
    binary_data = b"\x00\xff\x00\xff" * 10
    binary_file.write_bytes(binary_data)

    # Test file with high ASCII characters
    high_ascii_file = project_env / "high_ascii.txt"
    high_ascii_content = "Test with high ASCII: é ñ ü ß ¥"
    high_ascii_file.write_text(high_ascii_content)

    try:
        # Binary files should be ignored
        assert await collector.should_ignore_file(binary_file)
        # Files with high ASCII should be ignored
        assert await collector.should_ignore_file(high_ascii_file)
    finally:
        # Cleanup
        binary_file.unlink()
        high_ascii_file.unlink()


@pytest.mark.asyncio
async def test_sync_ignore_patterns(project_env: Path) -> None:
    """Test synchronous ignore pattern handling through collect_files."""
    collector = Collector(project_env)
    collector.ignore_patterns = ["*.log", "node_modules/"]

    # Create test files
    test_files = [
        "test.log",  # Should be ignored
        "node_modules/test.js",  # Should be ignored
        "test.py",  # Should not be ignored
        "src/main.js",  # Should not be ignored
    ]

    for file_path in test_files:
        path = project_env / file_path
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text("Test content")

    try:
        # Collect files and verify ignore patterns work
        files = await collector.collect_files(str(project_env))
        collected_names = [p.name for p in files]

        assert "test.log" not in collected_names
        assert "test.js" not in collected_names
        assert "test.py" in collected_names
        assert "main.js" in collected_names

    finally:
        # Cleanup
        for file_path in test_files:
            path = project_env / file_path
            path.unlink()
            if path.parent != project_env:
                path.parent.rmdir()


@pytest.mark.asyncio
async def test_should_ignore_file_special_cases(project_env: Path) -> None:
    """Test special cases for file ignore logic."""
    collector = Collector(project_env)

    # Test FULL_CODE_ files
    assert await collector.should_ignore_file(project_env / "FULL_CODE_test.md")

    # Test .neuroloraignore file
    assert await collector.should_ignore_file(project_env / ".neuroloraignore")

    # Test file with permission error
    no_access_file = project_env / "no_access.txt"
    no_access_file.write_text("Test content")
    os.chmod(no_access_file, 0o000)
    try:
        assert await collector.should_ignore_file(no_access_file)
    finally:
        os.chmod(no_access_file, 0o666)
        no_access_file.unlink()

    # Test directory patterns
    assert await collector.should_ignore_file(
        project_env / "node_modules" / "deep" / "test.js"
    )
    assert await collector.should_ignore_file(project_env / "dist" / "index.html")

    # Test file outside project root
    outside_file = project_env.parent / "outside.py"
    outside_file.touch()
    assert not await collector.should_ignore_file(outside_file)
    outside_file.unlink()


@pytest.mark.asyncio
async def test_collect_files_error_handling(project_env: Path) -> None:
    """Test error handling in collect_files."""
    collector = Collector(project_env)

    # Test permission error
    no_access_dir = project_env / "no_access"
    no_access_dir.mkdir()
    no_access_file = no_access_dir / "test.py"
    no_access_file.write_text("Test content")

    os.chmod(no_access_dir, 0o000)
    files = await collector.collect_files(str(no_access_dir))
    assert files == []
    os.chmod(no_access_dir, 0o777)

    no_access_file.unlink()
    no_access_dir.rmdir()

    # Test invalid path
    files = await collector.collect_files("\0invalid")  # Invalid path character
    assert files == []  # Should return empty list for invalid paths

    # Test collecting from multiple paths with some failing
    test_file = project_env / "test.py"
    test_file.write_text("Test content")

    files = await collector.collect_files([str(test_file), "nonexistent", "\0invalid"])
    assert len(files) == 1
    assert test_file in files

    test_file.unlink()


@pytest.mark.asyncio
async def test_collect_files_sorting(project_env: Path) -> None:
    """Test file sorting in collect_files."""
    collector = Collector(project_env)

    # Create test files
    files = ["b.py", "a.py", "PROJECT_SUMMARY.md", "src/test.py", "README.md"]

    for file in files:
        path = project_env / file
        path.parent.mkdir(exist_ok=True)
        path.write_text("Test content")

    collected = await collector.collect_files(str(project_env))

    # PROJECT_SUMMARY.md should be first
    assert collected[0].name == "PROJECT_SUMMARY.md"

    # Other files should be sorted alphabetically
    sorted_names = [f.name for f in collected[1:]]
    assert sorted_names == ["README.md", "a.py", "b.py", "test.py"]

    # Cleanup
    for file in files:
        path = project_env / file
        path.unlink()
        if path.parent != project_env:
            path.parent.rmdir()
