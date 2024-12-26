"""Module for analyzing and reporting project structure metrics.

This module provides functionality to analyze project structure, including:
- File size analysis
- Line counting
- Token estimation
- Report generation in markdown format
"""

import fnmatch
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, TypedDict


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
        self.large_file_threshold = 1024 * 1024  # 1MB
        self.large_lines_threshold = 300

        # Load ignore patterns from .neuroloraignore and combine with provided
        # patterns
        self.ignore_patterns = self.load_ignore_patterns()
        if ignore_patterns:
            self.ignore_patterns.extend(ignore_patterns)

    def load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .neuroloraignore file.

        Returns:
            List[str]: List of ignore patterns
        """
        # Check for .neuroloraignore file
        ignore_file = self.root_dir / ".neuroloraignore"
        patterns: List[str] = []

        try:
            if ignore_file.exists():
                with open(ignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            patterns.append(line)
        except (
            FileNotFoundError,
            PermissionError,
            UnicodeDecodeError,
            IOError,
        ):
            pass

        return patterns

    def should_ignore(self, path: Path) -> bool:
        """Check if file/directory should be ignored based on patterns.

        Args:
            path: Path to check

        Returns:
            bool: True if path should be ignored
        """
        try:
            relative_path = path.relative_to(self.root_dir)
            str_path = str(relative_path)

            # Check each ignore pattern
            for pattern in self.ignore_patterns:
                # Handle directory patterns (ending with /)
                if pattern.endswith("/"):
                    if any(
                        part == pattern[:-1] for part in relative_path.parts
                    ):
                        return True
                # Handle file patterns
                elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                    path.name, pattern
                ):
                    return True

            # Additional checks
            if "FULL_CODE_" in str(path):
                return True

            # Always ignore .neuroloraignore files
            if path.name == ".neuroloraignore":
                return True

            try:
                if (
                    path.exists() and path.stat().st_size > 1024 * 1024
                ):  # Skip files > 1MB
                    return True
            except (FileNotFoundError, PermissionError):
                return True

            return False
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
            # Try to detect if file is binary
            with open(filepath, "rb") as f:
                chunk = f.read(1024)
                if b"\0" in chunk:  # Binary file detection
                    return 0

            # If not binary, count lines
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
            # Header
            f.write("# Project Structure Report\n\n")
            f.write(
                "Description: Project structure analysis with metrics "
                "and recommendations\n"
            )
            f.write(f"Generated: {report_data['last_updated']}\n\n")

            # Files section with tree structure
            f.write("## Project Tree\n\n")
            files = sorted(report_data["files"], key=lambda x: x["path"])

            # Build tree structure
            current_path: List[str] = []
            for file_data in files:
                parts = file_data["path"].split("/")

                # Find common prefix
                i = 0
                while i < len(current_path) and i < len(parts) - 1:
                    if current_path[i] != parts[i]:
                        break
                    i += 1

                # Remove different parts
                while len(current_path) > i:
                    current_path.pop()

                # Add new parts
                while i < len(parts) - 1:
                    f.write("│   " * len(current_path))
                    f.write("├── " + parts[i] + "/\n")
                    current_path.append(parts[i])
                    i += 1

                # Write file entry
                f.write("│   " * len(current_path))
                f.write("├── ")
                self._write_file_entry(f, file_data, tree_format=True)

            # Summary
            f.write("\n## Summary\n\n")
            total_kb = report_data["total_size"] / 1024
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Total Size | {total_kb:.1f}KB |\n")
            f.write(f"| Total Lines | {report_data['total_lines']} |\n")
            f.write(f"| Total Tokens | ~{report_data['total_tokens']} |\n")
            f.write(f"| Large Files | {report_data['large_files']} |\n")
            if report_data["error_files"] > 0:
                f.write(
                    f"| Files with Errors | {report_data['error_files']} |\n"
                )

            # Notes
            f.write("\n## Notes\n\n")
            f.write("- 📦 File size indicators:\n")
            f.write("  - Files larger than 1MB are marked as large files\n")
            f.write(
                "  - Size is shown in KB for files ≥ 1KB, " "bytes otherwise\n"
            )
            f.write("- 📊 Code metrics:\n")
            f.write("  - 🔴 indicates files with more than 300 lines\n")
            f.write("  - Token count is estimated (4 chars ≈ 1 token)\n")
            f.write("  - Empty lines are excluded from line count\n")
            f.write("- ⚠️ Processing:\n")
            f.write(
                "  - Binary files and files with encoding errors "
                "are skipped\n"
            )
            f.write("  - Files matching ignore patterns are excluded\n\n")

            # Recommendations
            f.write("## Recommendations\n\n")
            f.write(
                "The following files might benefit from being split "
                "into smaller modules:\n\n"
            )
            complex_files = [f for f in files if f["is_complex"]]
            if complex_files:
                for file_data in sorted(
                    complex_files, key=lambda x: x["lines"], reverse=True
                ):
                    lines = file_data["lines"]
                    suggested_modules = self._calculate_suggested_modules(
                        lines
                    )
                    avg_lines = lines // suggested_modules
                    f.write(f"- {file_data['path']} ({lines} lines) 🔴\n")
                    f.write(
                        f"  - Consider splitting into {suggested_modules} "
                        f"modules of ~{avg_lines} lines each\n"
                    )
            else:
                f.write(
                    "No files currently exceed the recommended "
                    "size limit (300 lines).\n"
                )

    def _calculate_suggested_modules(self, lines: int) -> int:
        """Calculate suggested number of modules for splitting a file.

        Args:
            lines: Number of lines in the file

        Returns:
            int: Suggested number of modules
        """
        return (
            lines + self.large_lines_threshold - 1
        ) // self.large_lines_threshold

    def _write_file_entry(
        self, f: Any, file_data: FileData, tree_format: bool = False
    ) -> None:
        """Write a single file entry in the report.

        Args:
            f: File handle to write to
            file_data: Data for the file entry
        """
        size_kb = file_data["size_bytes"] / 1024
        size_str = (
            f"{size_kb:.1f}KB"
            if size_kb >= 1
            else f"{file_data['size_bytes']}B"
        )

        filename = file_data["path"].split("/")[-1]
        if file_data.get("error", False):
            f.write(f"{filename} (⚠️ Error accessing file)\n")
        elif file_data["is_large"]:
            f.write(f"{filename} ({size_str}) ⚠️ Large file\n")
        else:
            complexity_marker = "🔴" if file_data["is_complex"] else ""
            f.write(
                f"{filename} ({size_str}, ~{file_data['tokens']} tokens, "
                f"{file_data['lines']} lines) {complexity_marker}\n"
            )
