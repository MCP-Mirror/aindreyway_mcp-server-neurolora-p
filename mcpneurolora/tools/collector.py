"""Code collection functionality."""

import fnmatch
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ..file_naming import FileType, format_filename, get_file_pattern
from ..log_utils import LogCategory, get_logger
from ..storage import StorageManager
from ..utils import async_io
from ..utils.validation import validate_path

# Get module logger
logger = get_logger(__name__, LogCategory.TOOLS)


class LanguageMap:
    """Mapping of file extensions to markdown code block languages."""

    EXTENSIONS: Dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".md": "markdown",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".bat": "batch",
        ".ps1": "powershell",
        ".sql": "sql",
        ".java": "java",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".rs": "rust",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".r": "r",
        ".lua": "lua",
        ".m": "matlab",
        ".pl": "perl",
        ".xml": "xml",
        ".toml": "toml",
        ".ini": "ini",
        ".conf": "conf",
    }

    @classmethod
    def get_language(cls, file_path: Path) -> str:
        """Get language identifier for a file extension.

        Args:
            file_path: Path to get extension from.

        Returns:
            str: Language identifier for markdown code block.
        """
        return cls.EXTENSIONS.get(file_path.suffix.lower(), "")


class Collector:
    """Main class for collecting and processing code files."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
    ) -> None:
        """Initialize the Collector.

        Args:
            project_root: Optional path to project root directory.
                        If not provided, uses current working directory.

        Raises:
            RuntimeError: If storage setup fails.
        """
        # Get the project root directory
        self.project_root = project_root or Path.cwd()

        # Initialize and setup storage manager
        self.storage = StorageManager(project_root)
        try:
            self.storage.setup()
            logger.info("Storage setup completed successfully")
        except Exception as err:
            logger.error("Failed to setup storage: %s", str(err))
            raise RuntimeError(f"Storage setup failed: {str(err)}")

        # Load ignore patterns
        self.ignore_patterns: List[str] = []

    async def load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .neuroloraignore file.

        Returns:
            List[str]: List of ignore patterns
        """
        # First check for user's .neuroloraignore
        ignore_file = self.project_root / ".neuroloraignore"
        logger.debug("Looking for ignore file at: %s", ignore_file)

        patterns: List[str] = []
        try:
            if await async_io.path_exists(ignore_file):
                content = await async_io.read_file(ignore_file)
                for line in content.splitlines():
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
                logger.debug("Loaded %d ignore patterns", len(patterns))
            else:
                logger.debug("No .neuroloraignore found, using empty patterns")
        except Exception as err:
            logger.error("Error loading .neuroloraignore: %s", str(err))

        return patterns

    async def should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored based on patterns.

        Args:
            file_path: Path to check.

        Returns:
            bool: True if file should be ignored, False otherwise.
        """
        # Validate and get relative path
        file_path = validate_path(file_path)
        try:
            relative_path = file_path.relative_to(self.project_root)
            logger.debug("Checking path: %s (from %s)", relative_path, file_path)
        except ValueError:
            relative_path = file_path
            logger.debug("Using absolute path: %s", file_path)

        str_path = str(relative_path)

        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                if any(part == pattern[:-1] for part in relative_path.parts):
                    logger.debug("Ignoring by directory pattern: %s", pattern)
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                file_path.name, pattern
            ):
                logger.debug("Ignoring by file pattern: %s", pattern)
                return True

        # Check for generated files using new naming patterns
        for file_type in FileType:
            if get_file_pattern(file_type).search(str(file_path)):
                logger.debug("Ignoring generated file: %s", file_type)
                return True

        # Always ignore .neuroloraignore files
        if file_path.name == ".neuroloraignore":
            logger.debug("Ignoring .neuroloraignore file")
            return True

        try:
            # Check file permissions
            if not os.access(str(file_path), os.R_OK):
                logger.error("Permission denied accessing file: %s", file_path)
                return True

            # Check file size
            size = await async_io.get_file_size(file_path)
            if size and size > 1024 * 1024:  # 1MB
                logger.debug(
                    "Ignoring large file (%d bytes): %s",
                    size,
                    file_path,
                )
                return True

            # Try to read file content in binary mode first
            try:
                with open(file_path, "rb") as f:
                    binary_content = f.read(1024)  # Read first 1KB to check
                    if b"\x00" in binary_content:  # Check for null bytes
                        logger.warning("Binary file detected: %s", file_path)
                        return True
            except Exception as err:
                logger.error("Error reading file in binary mode: %s", str(err))
                return True

            # Try to read as text
            try:
                text_content = await async_io.read_file(file_path)
                # Check if content has high ASCII characters
                for char in text_content:
                    if ord(char) > 127:
                        logger.warning("Binary file detected: %s", file_path)
                        return True
            except (UnicodeDecodeError, PermissionError) as err:
                if isinstance(err, UnicodeDecodeError):
                    logger.warning("Binary file detected: %s", file_path)
                else:
                    logger.error("Permission denied accessing file: %s", file_path)
                return True
            except Exception as err:
                logger.error("Error reading file: %s", str(err))
                return True

            # File is readable, not binary, and not too large
            logger.debug("File will be included: %s", file_path)
            return False

        except Exception as err:
            logger.error("Error checking file %s: %s", str_path, str(err))
            return True

    def make_anchor(self, path: Union[str, Path]) -> str:
        """Create a valid markdown anchor from a path.

        Args:
            path: Path to convert to anchor.

        Returns:
            str: Valid markdown anchor.
        """
        anchor = str(path).lower()
        return anchor.replace("/", "-").replace(".", "-").replace(" ", "-")

    def _check_ignore_patterns(self, path: Path) -> bool:
        """Check if path matches any ignore patterns.

        Args:
            path: Path to check

        Returns:
            bool: True if path should be ignored
        """
        # Validate and get relative path
        path = validate_path(path)
        try:
            relative_path = path.relative_to(self.project_root)
            logger.debug("Checking path: %s (from %s)", relative_path, path)
        except ValueError:
            relative_path = path
            logger.debug("Using absolute path: %s", path)

        str_path = str(relative_path)

        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                if any(part == pattern[:-1] for part in relative_path.parts):
                    logger.debug("Ignoring by directory pattern: %s", pattern)
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                path.name, pattern
            ):
                logger.debug("Ignoring by file pattern: %s", pattern)
                return True

        # Check for generated files using new naming patterns
        for file_type in FileType:
            if get_file_pattern(file_type).search(str(path)):
                logger.debug("Ignoring generated file: %s", file_type)
                return True

        # Always ignore .neuroloraignore files
        if path.name == ".neuroloraignore":
            logger.debug("Ignoring .neuroloraignore file")
            return True

        logger.debug("File will be included: %s", path)
        return False

    def _make_sync_ignore_func(self) -> Callable[[Path], bool]:
        """Create a synchronous version of should_ignore_file.

        Returns:
            Callable[[Path], bool]: Synchronous ignore function
        """
        return self._check_ignore_patterns

    async def collect_files(self, input_paths: Union[str, List[str]]) -> List[Path]:
        """Collect all relevant files from input paths.

        Args:
            input_paths: Path(s) to process.

        Returns:
            List[Path]: List of files to process.
        """
        # Convert single path to list
        if isinstance(input_paths, str):
            input_paths = [input_paths]

        # Load ignore patterns if not already loaded
        if not self.ignore_patterns:
            self.ignore_patterns = await self.load_ignore_patterns()
            logger.debug("Using ignore patterns: %s", self.ignore_patterns)

        all_files: List[Path] = []
        for input_path in input_paths:
            try:
                # Convert relative path to absolute using project_root
                path = Path(input_path)
                if not path.is_absolute():
                    path = (self.project_root / path).resolve()
                else:
                    path = path.resolve()
                logger.debug("Processing path: %s", path)
            except (ValueError, RuntimeError) as err:
                logger.error("Invalid path format %s: %s", input_path, str(err))
                continue

            if not await async_io.path_exists(path):
                logger.error("Path does not exist: %s", path)
                continue

            # Check if it's a directory
            is_directory = await async_io.is_dir(path)
            if is_directory:
                logger.debug("Walking directory: %s", path)
                # It's a directory, walk through it and collect only files
                files = await async_io.walk_directory(
                    path, self._make_sync_ignore_func()
                )
                logger.debug("Found %d files in directory", len(files))
                for file_path in files:
                    if not await async_io.is_dir(file_path):
                        logger.debug("Checking file: %s", file_path)
                        should_ignore = await self.should_ignore_file(file_path)
                        if should_ignore:
                            logger.debug("Ignoring file: %s", file_path)
                        else:
                            all_files.append(file_path)
                            logger.debug("Added file from directory: %s", file_path)
            else:
                # It's a file, check if we should include it
                logger.debug("Checking single file: %s", path)
                should_ignore = await self.should_ignore_file(path)
                if should_ignore:
                    logger.debug("Ignoring single file: %s", path)
                else:
                    all_files.append(path)
                    logger.debug("Added single file: %s", path)

        # Sort files with PROJECT_SUMMARY.md first
        def sort_key(path: Path) -> tuple[int, str]:
            try:
                relative_path = path.relative_to(self.project_root)
            except ValueError:
                relative_path = path
            # Sort order: PROJECT_SUMMARY.md first, then alphabetically
            is_summary = relative_path.name == "PROJECT_SUMMARY.md"
            return (0 if is_summary else 1, str(relative_path))

        sorted_files = sorted(all_files, key=sort_key)
        logger.info("Collected %d files total", len(sorted_files))
        return sorted_files

    async def collect_code(
        self,
        input_paths: Union[str, List[str]],
    ) -> Optional[Path]:
        """Process all files and generate markdown documentation.

        Args:
            input_paths: Path(s) to process.

        Returns:
            Optional[Path]: Path to generated markdown file or None if failed.
            The path is returned as a Path object if successful,
            None if failed.
        """
        try:
            # Get all files and filter out directories first
            all_files = await self.collect_files(input_paths)
            if not all_files:
                logger.warning("No files found to process")
                return None

            # Filter out directories immediately
            files_to_process: List[Path] = []
            for file_path in all_files:
                try:
                    if await async_io.is_dir(file_path):
                        logger.debug(
                            "Skipping directory: %s\n"
                            "Current working directory: %s\n"
                            "Absolute path: %s\n"
                            "Parent directory: %s\n"
                            "Directory name: %s",
                            file_path,
                            Path.cwd(),
                            file_path.absolute(),
                            file_path.parent,
                            file_path.name,
                        )
                        continue
                    files_to_process.append(file_path)
                except Exception as err:
                    logger.error("Error checking path %s: %s", file_path, str(err))
                    continue

            if not files_to_process:
                logger.warning("No files found to process after filtering directories")
                return None

            # Create output files with new naming scheme
            code_output_path = self.storage.get_output_path(
                format_filename(FileType.CODE)
            )

            # Create parent directory if it doesn't exist
            await async_io.ensure_dir(code_output_path.parent)

            # Build code collection content
            content: List[str] = ["# Code Collection\n\n"]
            content.append(
                "This file contains code from the specified paths, "
                "organized by file path.\n\n"
            )

            # Add table of contents
            content.append("## Table of Contents\n\n")
            for file_path in files_to_process:
                try:
                    relative_path = file_path.relative_to(self.project_root)
                except ValueError:
                    relative_path = file_path
                anchor = self.make_anchor(str(relative_path))
                content.append(f"- [{relative_path}](#{anchor})\n")

            # Add file contents
            content.append("\n## Files\n\n")
            for file_path in files_to_process:
                # Get relative path and create anchor first
                try:
                    relative_path = file_path.relative_to(self.project_root)
                except ValueError:
                    relative_path = file_path
                anchor = self.make_anchor(str(relative_path))

                try:
                    file_content = await async_io.read_file(file_path)
                    lang = LanguageMap.get_language(file_path)

                    content.append(f"### {relative_path} {{{anchor}}}\n")
                    content.append(f"```{lang}\n{file_content}\n```\n\n")
                    logger.debug("Processed file: %s", relative_path)
                except Exception as err:
                    logger.error("Error processing file %s: %s", file_path, str(err))
                    content.append(f"### {relative_path} {{{anchor}}}\n")
                    content.append(f"```\n[Error reading file: {str(err)}]\n```\n\n")

            # Write code collection file
            await async_io.write_file(code_output_path, "".join(content))

            # Create analysis prompt file with new naming scheme
            analyze_output_path = self.storage.get_output_path(
                format_filename(FileType.IMPROVE_PROMPT)
            )
            prompt_path = Path(__file__).parent.parent / "prompts" / "improve.prompt.md"

            # Read code content and prompt
            code_content = await async_io.read_file(code_output_path)
            prompt_content = await async_io.read_file(prompt_path)

            # Write analysis file
            await async_io.write_file(
                analyze_output_path, prompt_content + "\n" + code_content
            )

            # Verify files exist
            if not await async_io.path_exists(code_output_path):
                raise RuntimeError(f"Failed to create code file: {code_output_path}")
            if not await async_io.path_exists(analyze_output_path):
                raise RuntimeError(
                    f"Failed to create analysis file: {analyze_output_path}"
                )

            # Calculate approximate token count
            # Using rough estimate: 4 chars per token
            code_content = await async_io.read_file(code_output_path)
            token_count = len(code_content) // 4

            logger.info("Analysis prompt created: %s", analyze_output_path)
            logger.info(
                "Code collection complete! (Approx. %d tokens)",
                token_count,
            )
            return Path(code_output_path)

        except (ValueError, TypeError) as err:
            logger.error("Invalid input error during code collection: %s", str(err))
            return None
        except OSError as err:
            logger.error("System error during code collection: %s", str(err))
            return None
        except Exception as err:
            logger.error("Runtime error during code collection: %s", str(err))
            return None
