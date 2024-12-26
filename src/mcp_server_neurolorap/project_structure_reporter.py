"""Module for analyzing and reporting project structure metrics.

This module provides functionality to analyze project structure, including:
- File size analysis
- Line counting
- Token estimation
- Report generation in markdown format
"""

import os
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import List, Optional, TypedDict


class FileData(TypedDict):
    """Type definition for file analysis data."""

    path: str
    size_bytes: int
    tokens: int
    lines: int
    is_large: bool
    is_complex: bool
    error: bool


class ReportData(TypedDict):
    """Type definition for project analysis report."""

    last_updated: str
    files: List[FileData]
    total_size: int
    total_lines: int
    total_tokens: int
    large_files: int
    error_files: int


class ProjectStructureReporter:
    """Analyzes project structure and generates reports on file metrics."""

    def __init__(
        self, root_dir: Path, ignore_patterns: Optional[List[str]] = None
    ):
        """Initialize reporter with root directory and ignore patterns.

        Args:
            root_dir: Root directory to analyze
            ignore_patterns: List of patterns to ignore (glob format)
        """
        self.root_dir = root_dir
        self.ignore_patterns = ignore_patterns or []
        self.large_file_threshold = 1024 * 1024  # 1MB
        self.large_lines_threshold = 300

    def should_ignore(self, path: Path) -> bool:
        """Check if file/directory should be ignored based on patterns.

        Args:
            path: Path to check

        Returns:
            bool: True if path should be ignored
        """
        try:
            relative_path = str(path.relative_to(self.root_dir))
            return any(
                fnmatch.fnmatch(relative_path, pattern)
                for pattern in self.ignore_patterns
            )
        except ValueError:
            return True

    def count_lines(self, filepath: Path) -> int:
        """Count non-empty lines in file.

        Args:
            filepath: Path to file

        Returns:
            int: Number of non-empty lines
        """
        try:
            with filepath.open("r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except (UnicodeDecodeError, OSError):
            return 0

    def estimate_tokens(self, size_bytes: int) -> int:
        """Estimate number of tokens based on file size.

        Args:
            size_bytes: File size in bytes

        Returns:
            int: Estimated number of tokens (4 chars ≈ 1 token)
        """
        return size_bytes // 4

    def analyze_file(self, filepath: Path) -> FileData:
        """Analyze single file metrics.

        Args:
            filepath: Path to file

        Returns:
            dict: File metrics including size, lines, and tokens
        """
        try:
            size_bytes = filepath.stat().st_size

            # Skip detailed analysis for large files
            if size_bytes > self.large_file_threshold:
                return {
                    "path": str(filepath.relative_to(self.root_dir)),
                    "size_bytes": size_bytes,
                    "tokens": 0,
                    "lines": 0,
                    "is_large": True,
                    "is_complex": False,
                    "error": False,
                }

            lines = self.count_lines(filepath)
            tokens = self.estimate_tokens(size_bytes)

            return {
                "path": str(filepath.relative_to(self.root_dir)),
                "size_bytes": size_bytes,
                "tokens": tokens,
                "lines": lines,
                "is_large": False,
                "is_complex": lines > self.large_lines_threshold,
                "error": False,
            }
        except OSError:
            # Handle file access errors gracefully
            return {
                "path": str(filepath.relative_to(self.root_dir)),
                "size_bytes": 0,
                "tokens": 0,
                "lines": 0,
                "is_large": False,
                "is_complex": False,
                "error": True,
            }

    def analyze_project_structure(self) -> ReportData:
        """Analyze entire project structure.

        Returns:
            dict: Project metrics including all files and totals
        """
        report_data: ReportData = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "files": [],
            "total_size": 0,
            "total_lines": 0,
            "total_tokens": 0,
            "large_files": 0,
            "error_files": 0,
        }

        for dirpath, dirs, files in os.walk(self.root_dir):
            current_path = Path(dirpath)

            # Skip ignored directories
            dirs[:] = [
                d for d in dirs if not self.should_ignore(current_path / d)
            ]

            for filename in files:
                filepath = current_path / filename
                if self.should_ignore(filepath):
                    continue

                file_data = self.analyze_file(filepath)
                report_data["files"].append(file_data)

                report_data["total_size"] += file_data["size_bytes"]
                if file_data.get("error", False):
                    report_data["error_files"] += 1
                elif file_data["is_large"]:
                    report_data["large_files"] += 1
                else:
                    report_data["total_lines"] += file_data["lines"]
                    report_data["total_tokens"] += file_data["tokens"]

        return report_data

    def generate_markdown_report(
        self, report_data: ReportData, output_path: Path
    ) -> None:
        """Generate markdown report from analysis data.

        Args:
            report_data: Analysis results
            output_path: Where to save the report
        """
        with output_path.open("w", encoding="utf-8") as f:
            f.write("# Project Structure Report\n\n")
            f.write(f"Generated: {report_data['last_updated']}\n\n")

            f.write("## Files\n\n")
            for file_data in sorted(
                report_data["files"], key=lambda x: x["path"]
            ):
                size_kb = file_data["size_bytes"] / 1024
                size_str = (
                    f"{size_kb:.1f}KB"
                    if size_kb >= 1
                    else f"{file_data['size_bytes']}B"
                )

                if file_data.get("error", False):
                    f.write(
                        f"- {file_data['path']} (⚠️ Error accessing file)\n"
                    )
                elif file_data["is_large"]:
                    f.write(
                        f"- {file_data['path']} ({size_str}) ⚠️ Large file\n"
                    )
                else:
                    complexity_marker = "🔴" if file_data["is_complex"] else ""
                    f.write(
                        f"- {file_data['path']} "
                        f"({size_str}, ~{file_data['tokens']} tokens, "
                        f"{file_data['lines']} lines) {complexity_marker}\n"
                    )

            f.write("\n## Summary\n\n")
            total_kb = report_data["total_size"] / 1024
            f.write(f"Total size: {total_kb:.1f}KB\n")
            f.write(f"Total lines: {report_data['total_lines']}\n")
            f.write(f"Total tokens: ~{report_data['total_tokens']}\n")
            f.write(f"Large files: {report_data['large_files']}\n")
            if report_data["error_files"] > 0:
                f.write(f"Files with errors: {report_data['error_files']}\n")

            f.write("\n## Notes\n\n")
            f.write("- Files larger than 1MB are marked as large files\n")
            f.write("- Files with more than 300 lines are marked with 🔴\n")
            f.write("- Token count is estimated (4 chars ≈ 1 token)\n")
            f.write("- Empty lines are excluded from line count\n")
            f.write(
                "- Binary files and files with encoding errors are skipped\n"
            )
