"""Project structure analysis and reporting."""

import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, TypedDict, cast

from ..file_naming import FileType, format_filename, get_file_pattern
from ..log_utils import LogCategory, get_logger
from ..storage import StorageManager
from ..utils import async_io

# Get module logger
logger = get_logger(__name__, LogCategory.TOOLS)


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


class Reporter:
    """Main class for analyzing project structure."""

    def __init__(
        self, root_dir: Path, ignore_patterns: Optional[List[str]] = None
    ) -> None:
        """Initialize the Reporter.

        Args:
            root_dir: Root directory to analyze
            ignore_patterns: List of patterns to ignore (glob format)
        """
        self.root_dir = root_dir
        self.large_file_threshold = 1024 * 1024  # 1MB
        self.large_lines_threshold = 300

        # Initialize storage manager
        self.storage = StorageManager(root_dir)
        self.storage.setup()

        # Initialize ignore patterns
        self.ignore_patterns: List[str] = []
        if ignore_patterns:
            self.ignore_patterns.extend(ignore_patterns)

    async def load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .neuroloraignore file.

        Returns:
            List[str]: List of ignore patterns
        """
        # Check for .neuroloraignore file
        ignore_file = self.root_dir / ".neuroloraignore"
        patterns: List[str] = []

        try:
            if await async_io.path_exists(ignore_file):
                content = await async_io.read_file(ignore_file)
                for line in content.splitlines():
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception as e:
            logger.error(f"Error loading .neuroloraignore: {str(e)}")

        return patterns

    async def should_ignore(self, path: Path) -> bool:
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

            # Check for generated files using new naming patterns
            for file_type in FileType:
                if get_file_pattern(file_type).match(str(path)):
                    return True

            # Always ignore .neuroloraignore files
            if path.name == ".neuroloraignore":
                return True

            try:
                size = await async_io.get_file_size(path)
                if size and size > self.large_file_threshold:
                    return True
            except Exception as e:
                logger.error(f"Error checking file size: {str(e)}")
                return True

            return False
        except ValueError:
            return True

    async def analyze_file(self, filepath: Path) -> FileData:
        """Analyze single file metrics.

        Args:
            filepath: Path to file

        Returns:
            FileData: File metrics including size, lines, and tokens
        """
        try:
            size = await async_io.get_file_size(filepath)
            if not size:
                raise FileNotFoundError(f"Could not get size for {filepath}")

            # Skip detailed analysis for large files
            if size > self.large_file_threshold:
                return cast(
                    FileData,
                    {
                        "path": str(filepath.relative_to(self.root_dir)),
                        "size_bytes": size,
                        "tokens": 0,
                        "lines": 0,
                        "is_large": True,
                        "is_complex": False,
                        "error": False,
                    },
                )

            lines = await async_io.count_lines(filepath)
            tokens = self.estimate_tokens(size)

            return cast(
                FileData,
                {
                    "path": str(filepath.relative_to(self.root_dir)),
                    "size_bytes": size,
                    "tokens": tokens,
                    "lines": lines,
                    "is_large": False,
                    "is_complex": lines > self.large_lines_threshold,
                    "error": False,
                },
            )
        except Exception as e:
            logger.error(f"Error analyzing file {filepath}: {str(e)}")
            return cast(
                FileData,
                {
                    "path": str(filepath.relative_to(self.root_dir)),
                    "size_bytes": 0,
                    "tokens": 0,
                    "lines": 0,
                    "is_large": False,
                    "is_complex": False,
                    "error": True,
                },
            )

    def estimate_tokens(self, size_bytes: int) -> int:
        """Estimate number of tokens based on file size.

        Args:
            size_bytes: File size in bytes

        Returns:
            int: Estimated number of tokens (4 chars ≈ 1 token)
        """
        return size_bytes // 4

    def _make_sync_ignore_func(self: "Reporter") -> Callable[[Path], bool]:
        """Create a synchronous version of should_ignore.

        Returns:
            Callable[[Path], bool]: Synchronous ignore function
        """

        def sync_ignore(path: Path) -> bool:
            # Use synchronous checks only
            try:
                relative_path = path.relative_to(self.root_dir)
                str_path = str(relative_path)

                # Check patterns
                for pattern in self.ignore_patterns:
                    if pattern.endswith("/"):
                        if any(
                            part == pattern[:-1]
                            for part in relative_path.parts
                        ):
                            return True
                    elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                        path.name, pattern
                    ):
                        return True

                # Check generated files
                for file_type in FileType:
                    if get_file_pattern(file_type).search(str(path)):
                        return True

                # Always ignore .neuroloraignore
                if path.name == ".neuroloraignore":
                    return True

                return False
            except Exception:
                return True

        return sync_ignore

    async def analyze_project_structure(self) -> ReportData:
        """Analyze entire project structure.

        Returns:
            ReportData: Project metrics including all files and totals
        """
        # Load ignore patterns if not already loaded
        if not self.ignore_patterns:
            self.ignore_patterns = await self.load_ignore_patterns()

        report_data: ReportData = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "files": [],
            "total_size": 0,
            "total_lines": 0,
            "total_tokens": 0,
            "large_files": 0,
            "error_files": 0,
        }

        # Walk directory asynchronously
        all_files = await async_io.walk_directory(
            self.root_dir, self._make_sync_ignore_func()
        )

        # Analyze each file
        for filepath in all_files:
            file_data = await self.analyze_file(filepath)
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

    async def generate_report(self) -> Optional[Path]:
        """Generate project structure report.

        Returns:
            Optional[Path]: Path to generated report or None if failed
        """
        try:
            # Analyze project structure
            report_data = await self.analyze_project_structure()

            # Create output file with new naming scheme
            output_path = self.storage.get_output_path(
                format_filename(FileType.FULL_TREE)
            )

            # Generate markdown report
            await self.generate_markdown_report(report_data, output_path)

            return output_path
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None

    async def generate_markdown_report(
        self, report_data: ReportData, output_path: Path
    ) -> None:
        """Generate markdown report from analysis data.

        Args:
            report_data: Analysis results
            output_path: Where to save the report
        """
        # Build report content
        content: List[str] = []

        # Header
        content.append("# Project Structure Report\n\n")
        content.append(
            "Description: Project structure analysis with metrics "
            "and recommendations\n"
        )
        content.append(f"Generated: {report_data['last_updated']}\n\n")

        # Files section with tree structure
        content.append("## Project Tree\n\n")
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
                content.append("│   " * len(current_path))
                content.append("├── " + parts[i] + "/\n")
                current_path.append(parts[i])
                i += 1

            # Write file entry
            content.append("│   " * len(current_path))
            content.append("├── ")
            content.append(self._format_file_entry(file_data))

        # Summary
        content.append("\n## Summary\n\n")
        total_kb = report_data["total_size"] / 1024
        content.append("| Metric | Value |\n")
        content.append("|--------|-------|\n")
        content.append(f"| Total Size | {total_kb:.1f}KB |\n")
        content.append(f"| Total Lines | {report_data['total_lines']} |\n")
        content.append(f"| Total Tokens | ~{report_data['total_tokens']} |\n")
        content.append(f"| Large Files | {report_data['large_files']} |\n")
        if report_data["error_files"] > 0:
            content.append(
                f"| Files with Errors | {report_data['error_files']} |\n"
            )

        # Notes
        content.append("\n## Notes\n\n")
        content.append("- 📦 File size indicators:\n")
        content.append("  - Files larger than 1MB are marked as large files\n")
        content.append(
            "  - Size is shown in KB for files ≥ 1KB, bytes otherwise\n"
        )
        content.append("- 📊 Code metrics:\n")
        content.append("  - 🔴 indicates files with more than 300 lines\n")
        content.append("  - Token count is estimated (4 chars ≈ 1 token)\n")
        content.append("  - Empty lines are excluded from line count\n")
        content.append("- ⚠️ Processing:\n")
        content.append(
            "  - Binary files and files with encoding errors " "are skipped\n"
        )
        content.append("  - Files matching ignore patterns are excluded\n\n")

        # Recommendations
        content.append("## Recommendations\n\n")
        content.append(
            "The following files might benefit from being split "
            "into smaller modules:\n\n"
        )
        complex_files = [f for f in files if f["is_complex"]]
        if complex_files:
            for file_data in sorted(
                complex_files, key=lambda x: x["lines"], reverse=True
            ):
                lines = file_data["lines"]
                suggested_modules = self._calculate_suggested_modules(lines)
                avg_lines = lines // suggested_modules
                content.append(
                    f"- {file_data['path']} ({lines} lines) 🔴\n"
                    f"  - Consider splitting into {suggested_modules} "
                    f"modules of ~{avg_lines} lines each\n"
                )
        else:
            content.append(
                "No files currently exceed the recommended "
                "size limit (300 lines).\n"
            )

        # Write report to file
        await async_io.write_file(output_path, "".join(content))

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

    def _format_file_entry(self, file_data: FileData) -> str:
        """Format a single file entry for the report.

        Args:
            file_data: Data for the file entry

        Returns:
            str: Formatted file entry
        """
        size_kb = file_data["size_bytes"] / 1024
        size_str = (
            f"{size_kb:.1f}KB"
            if size_kb >= 1
            else f"{file_data['size_bytes']}B"
        )

        filename = file_data["path"].split("/")[-1]
        if file_data.get("error", False):
            return f"{filename} (⚠️ Error accessing file)\n"
        elif file_data["is_large"]:
            return f"{filename} ({size_str}) ⚠️ Large file\n"
        else:
            complexity_marker = "🔴" if file_data["is_complex"] else ""
            tokens_str = f"~{file_data['tokens']} tokens"
            lines_str = f"{file_data['lines']} lines"
            return (
                f"{filename} ({size_str}, {tokens_str}, "
                f"{lines_str}) {complexity_marker}\n"
            )
