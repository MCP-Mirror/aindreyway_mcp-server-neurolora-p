"""Code collection functionality."""

import asyncio
import fnmatch
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ..file_naming import FileType, format_filename, get_file_pattern
from ..log_utils import LogCategory, get_logger
from ..storage import StorageManager
from ..utils import async_io

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
        """
        # Get the project root directory
        self.project_root = project_root or Path.cwd()

        # Initialize and setup storage manager
        self.storage = StorageManager(project_root)
        try:
            self.storage.setup()
            logger.info("Storage setup completed successfully")
        except Exception as e:
            logger.error("Failed to setup storage: %s", str(e))
            raise RuntimeError(f"Storage setup failed: {str(e)}")

        # Load ignore patterns
        self.ignore_patterns: List[str] = []

    async def load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .neuroloraignore file.

        Returns:
            List[str]: List of ignore patterns
        """
        # First check for user's .neuroloraignore
        ignore_file = self.project_root / ".neuroloraignore"
        logger.debug(f"Looking for ignore file at: {ignore_file}")

        patterns: List[str] = []
        try:
            if await async_io.path_exists(ignore_file):
                content = await async_io.read_file(ignore_file)
                for line in content.splitlines():
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
                logger.debug(f"Loaded {len(patterns)} ignore patterns")
            else:
                logger.debug("No .neuroloraignore found, using empty patterns")
        except Exception as e:
            logger.error(f"Error loading .neuroloraignore: {str(e)}")

        return patterns

    async def should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored based on patterns.

        Args:
            file_path: Path to check.

        Returns:
            bool: True if file should be ignored, False otherwise.
        """
        # Get relative path from project root
        try:
            relative_path = file_path.relative_to(self.project_root)
            logger.debug(f"Checking path: {relative_path} (from {file_path})")
        except ValueError:
            relative_path = file_path
            logger.debug(f"Using absolute path: {file_path}")

        str_path = str(relative_path)

        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                if any(part == pattern[:-1] for part in relative_path.parts):
                    logger.debug(f"Ignoring by directory pattern: {pattern}")
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                file_path.name, pattern
            ):
                logger.debug(f"Ignoring by file pattern: {pattern}")
                return True

        # Check for generated files using new naming patterns
        for file_type in FileType:
            pattern = get_file_pattern(file_type)
            if pattern.match(str(file_path)):
                logger.debug(f"Ignoring generated file: {file_type}")
                return True

        # Always ignore .neuroloraignore files
        if file_path.name == ".neuroloraignore":
            logger.debug("Ignoring .neuroloraignore file")
            return True

        try:
            # Handle large files (> 1MB)
            MAX_SIZE = 1024 * 1024  # 1MB
            size = await async_io.get_file_size(file_path)
            if size and size > MAX_SIZE:
                logger.debug(
                    f"Ignoring large file ({size} bytes): {file_path}"
                )
                return True
        except Exception as e:
            logger.error(f"Error checking file size for {str_path}: {str(e)}")
            return True

        logger.debug(f"File will be included: {file_path}")
        return False

    def make_anchor(self, path: Path) -> str:
        """Create a valid markdown anchor from a path.

        Args:
            path: Path to convert to anchor.

        Returns:
            str: Valid markdown anchor.
        """
        anchor = str(path).lower()
        return anchor.replace("/", "-").replace(".", "-").replace(" ", "-")

    def _make_sync_ignore_func(self) -> Callable[[Path], bool]:
        """Create a synchronous version of should_ignore_file.

        Returns:
            Callable[[Path], bool]: Synchronous ignore function
        """

        def sync_ignore(path: Path) -> bool:
            # Get relative path from project root
            try:
                relative_path = path.relative_to(self.project_root)
                logger.debug(f"Checking path: {relative_path} (from {path})")
            except ValueError:
                relative_path = path
                logger.debug(f"Using absolute path: {path}")

            str_path = str(relative_path)

            # Check each ignore pattern
            for pattern in self.ignore_patterns:
                # Handle directory patterns (ending with /)
                if pattern.endswith("/"):
                    if any(
                        part == pattern[:-1] for part in relative_path.parts
                    ):
                        logger.debug(
                            f"Ignoring by directory pattern: {pattern}"
                        )
                        return True
                # Handle file patterns
                elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                    path.name, pattern
                ):
                    logger.debug(f"Ignoring by file pattern: {pattern}")
                    return True

            # Check for generated files using new naming patterns
            for file_type in FileType:
                pattern = get_file_pattern(file_type)
                if pattern.match(str(path)):
                    logger.debug(f"Ignoring generated file: {file_type}")
                    return True

            # Always ignore .neuroloraignore files
            if path.name == ".neuroloraignore":
                logger.debug("Ignoring .neuroloraignore file")
                return True

            logger.debug(f"File will be included: {path}")
            return False

        return sync_ignore

    async def collect_files(
        self, input_paths: Union[str, List[str]]
    ) -> List[Path]:
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
            logger.debug(f"Using ignore patterns: {self.ignore_patterns}")

        all_files: List[Path] = []
        for input_path in input_paths:
            try:
                # Convert relative path to absolute using project_root
                path = Path(input_path)
                if not path.is_absolute():
                    path = (self.project_root / path).resolve()
                else:
                    path = path.resolve()
                logger.debug(f"Processing path: {path}")
            except (ValueError, RuntimeError) as e:
                logger.error(f"Invalid path format {input_path}: {str(e)}")
                continue

            if not await async_io.path_exists(path):
                logger.error(f"Path does not exist: {path}")
                continue

            # Check if it's a directory
            is_directory = await async_io.is_dir(path)
            if is_directory:
                logger.debug(f"Walking directory: {path}")
                # It's a directory, walk through it and collect only files
                files = await async_io.walk_directory(
                    path, self._make_sync_ignore_func()
                )
                logger.debug(f"Found {len(files)} files in directory")
                for file_path in files:
                    if not await async_io.is_dir(file_path):
                        logger.debug(f"Checking file: {file_path}")
                        should_ignore = await self.should_ignore_file(
                            file_path
                        )
                        if should_ignore:
                            logger.debug(f"Ignoring file: {file_path}")
                        else:
                            all_files.append(file_path)
                            logger.debug(
                                f"Added file from directory: {file_path}"
                            )
            else:
                # It's a file, check if we should include it
                logger.debug(f"Checking single file: {path}")
                should_ignore = await self.should_ignore_file(path)
                if should_ignore:
                    logger.debug(f"Ignoring single file: {path}")
                else:
                    all_files.append(path)
                    logger.debug(f"Added single file: {path}")

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
        logger.info(f"Collected {len(sorted_files)} files total")
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
            files_to_process = []
            for file_path in all_files:
                try:
                    if await async_io.is_dir(file_path):
                        logger.debug(
                            f"Skipping directory: {file_path}\n"
                            f"Current working directory: {Path.cwd()}\n"
                            f"Absolute path: {file_path.absolute()}\n"
                            f"Parent directory: {file_path.parent}\n"
                            f"Directory name: {file_path.name}"
                        )
                        continue
                    files_to_process.append(file_path)
                except Exception as e:
                    logger.error(f"Error checking path {file_path}: {str(e)}")
                    continue

            if not files_to_process:
                logger.warning(
                    "No files found to process after filtering directories"
                )
                return None

            # Create output files with new naming scheme
            code_output_path = self.storage.get_output_path(
                format_filename(FileType.CODE)
            )

            # Create parent directory if it doesn't exist
            await async_io.ensure_dir(code_output_path.parent)

            # Build code collection content
            content = ["# Code Collection\n\n"]
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
                anchor = self.make_anchor(relative_path)
                content.append(f"- [{relative_path}](#{anchor})\n")

            # Add file contents
            content.append("\n## Files\n\n")
            for file_path in files_to_process:
                # Get relative path and create anchor first
                try:
                    relative_path = file_path.relative_to(self.project_root)
                except ValueError:
                    relative_path = file_path
                anchor = self.make_anchor(relative_path)

                try:
                    file_content = await async_io.read_file(file_path)
                    lang = LanguageMap.get_language(file_path)

                    content.append(f"### {relative_path} {{{anchor}}}\n")
                    content.append(f"```{lang}\n{file_content}\n```\n\n")
                    logger.debug(f"Processed file: {relative_path}")
                except Exception as e:
                    logger.error(
                        f"Error processing file {file_path}: {str(e)}"
                    )
                    content.append(f"### {relative_path} {{{anchor}}}\n")
                    content.append(
                        f"```\n[Error reading file: {str(e)}]\n```\n\n"
                    )

            # Write code collection file
            await async_io.write_file(code_output_path, "".join(content))

            # Create analysis prompt file with new naming scheme
            analyze_output_path = self.storage.get_output_path(
                format_filename(FileType.IMPROVE_PROMPT)
            )
            prompt_path = (
                Path(__file__).parent.parent / "prompts" / "improve.prompt.md"
            )

            # Read code content and prompt
            code_content = await async_io.read_file(code_output_path)
            prompt_content = await async_io.read_file(prompt_path)

            # Write analysis file
            await async_io.write_file(
                analyze_output_path, prompt_content + "\n" + code_content
            )

            # Verify files exist
            if not await async_io.path_exists(code_output_path):
                raise RuntimeError(
                    f"Failed to create code file: {code_output_path}"
                )
            if not await async_io.path_exists(analyze_output_path):
                raise RuntimeError(
                    f"Failed to create analysis file: {analyze_output_path}"
                )

            # Calculate approximate token count
            # Using rough estimate: 4 chars per token
            code_content = await async_io.read_file(code_output_path)
            token_count = len(code_content) // 4

            logger.info(f"Analysis prompt created: {analyze_output_path}")
            logger.info(
                f"Code collection complete! (Approx. {token_count:,} tokens)"
            )
            return Path(code_output_path)

        except (ValueError, TypeError) as e:
            logger.error(
                f"Invalid input error during code collection: {str(e)}"
            )
            return None
        except OSError as e:
            logger.error(f"System error during code collection: {str(e)}")
            return None
        except RuntimeError as e:
            logger.error(f"Runtime error during code collection: {str(e)}")
            return None
