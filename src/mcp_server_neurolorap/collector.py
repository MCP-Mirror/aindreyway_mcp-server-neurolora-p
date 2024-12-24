"""Code collection functionality.

This module provides functionality to collect and document code files from
specified paths, creating a comprehensive markdown file containing the
contents of all relevant files.
"""

import fnmatch
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from .storage import StorageManager

# Get module logger
logger = logging.getLogger(__name__)


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


class CodeCollector:
    """Main class for collecting and processing code files."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        subproject_id: Optional[str] = None,
    ) -> None:
        """Initialize the CodeCollector.

        Args:
            project_root: Optional path to project root directory.
                        If not provided, uses current working directory.
            subproject_id: Optional subproject identifier.
                        If provided, will be appended to project name.
        """
        # Get the project root directory
        self.project_root = project_root or Path.cwd()
        logger.debug("Project root: %s", self.project_root)
        logger.debug("Current working directory: %s", Path.cwd())

        # Initialize storage manager
        self.storage = StorageManager(project_root, subproject_id)
        self.storage.setup()

        # Load ignore patterns
        self.ignore_patterns = self.load_ignore_patterns()

    def load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .neuroloraignore file.

        Returns:
            List[str]: List of ignore patterns
        """
        # First check for user's .neuroloraignore
        ignore_file = self.project_root / ".neuroloraignore"
        logger.debug(f"Looking for ignore file at: {ignore_file}")
        logger.debug(f"Ignore file exists: {ignore_file.exists()}")

        patterns: List[str] = []
        try:
            if ignore_file.exists():
                with open(ignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            patterns.append(line)
                logger.info(f"Loaded {len(patterns)} ignore patterns")
            else:
                logger.info("No .neuroloraignore found, using empty patterns")
        except FileNotFoundError:
            logger.warning("Could not find .neuroloraignore file")
        except PermissionError:
            logger.error("Permission denied accessing .neuroloraignore")
        except UnicodeDecodeError:
            logger.error("Invalid file encoding in .neuroloraignore")
        except IOError as e:
            logger.error(f"I/O error reading .neuroloraignore: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error loading .neuroloraignore: {str(e)}"
            )
            logger.debug("Stack trace:", exc_info=True)

        logger.info(f"Ignore patterns: {patterns}")
        return patterns

    def should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored based on patterns.

        Args:
            file_path: Path to check.

        Returns:
            bool: True if file should be ignored, False otherwise.
        """
        # Get relative path from project root
        try:
            relative_path = file_path.relative_to(self.project_root)
            logger.info(f"Checking relative path: {relative_path}")
        except ValueError:
            relative_path = file_path
            logger.info(f"Using absolute path: {relative_path}")

        str_path = str(relative_path)

        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                if any(part == pattern[:-1] for part in relative_path.parts):
                    logger.info(
                        f"Ignoring {str_path} (matches dir pattern {pattern})"
                    )
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                file_path.name, pattern
            ):
                logger.info(
                    f"Ignoring {str_path} (matches file pattern {pattern})"
                )
                return True

        # Additional checks
        if "FULL_CODE_" in str(file_path):
            logger.info(f"Ignoring {str_path} (generated file)")
            return True
        if file_path.stat().st_size > 1024 * 1024:  # Skip files > 1MB
            logger.info(f"Ignoring {str_path} (too large)")
            return True

        logger.info(f"Including {str_path}")
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

    def collect_files(self, input_paths: Union[str, List[str]]) -> List[Path]:
        """Collect all relevant files from input paths.

        Args:
            input_paths: Path(s) to process.

        Returns:
            List[Path]: List of files to process.
        """
        all_files: List[Path] = []

        # Convert single path to list
        if isinstance(input_paths, str):
            input_paths = [input_paths]

        logger.info(f"Processing input paths: {input_paths}")
        for input_path in input_paths:
            try:
                path = Path(input_path).resolve()
                logger.debug(f"Processing path: {path}")
                logger.debug(f"Path absolute: {path.absolute()}")
                logger.debug(f"Path exists: {path.exists()}")
                logger.debug(f"Path is file: {path.is_file()}")
                logger.debug(f"Path is dir: {path.is_dir()}")
                if not path.exists():
                    logger.error(f"Path does not exist: {path}")
                    continue
            except FileNotFoundError:
                logger.error(f"Path not found: {input_path}")
                continue
            except PermissionError:
                logger.error(f"Permission denied accessing path: {input_path}")
                continue
            except OSError as e:
                logger.error(
                    f"OS error processing path {input_path}: {str(e)}"
                )
                continue
            except Exception as e:
                logger.error(
                    f"Unexpected error processing path {input_path}: {str(e)}"
                )
                logger.debug("Stack trace:", exc_info=True)
                continue

            if path.is_file():
                if not self.should_ignore_file(path):
                    all_files.append(path)
            else:
                for root, dirs, files in os.walk(path):
                    root_path = Path(root)
                    logger.info(f"Walking directory: {root_path}")
                    # Remove ignored directories in-place
                    dirs[:] = [
                        d
                        for d in dirs
                        if not self.should_ignore_file(root_path / d)
                    ]
                    logger.info(f"Filtered directories: {dirs}")

                    for file in sorted(files):
                        file_path = root_path / file
                        if not self.should_ignore_file(file_path):
                            all_files.append(file_path)

        # Sort files with PROJECT_SUMMARY.md first
        def sort_key(path: Path) -> tuple[int, str]:
            try:
                relative_path = path.relative_to(self.project_root)
            except ValueError:
                relative_path = path
            # Sort order: PROJECT_SUMMARY.md first,
            # then alphabetically
            is_summary = relative_path.name == "PROJECT_SUMMARY.md"
            return (0 if is_summary else 1, str(relative_path))

        sorted_files = sorted(all_files, key=sort_key)
        logger.info(f"Found {len(sorted_files)} files to process")
        logger.info(f"Files to process: {sorted_files}")
        return sorted_files

    def read_file_content(self, file_path: Path) -> str:
        """Read content of a file with proper encoding handling.

        Args:
            file_path: Path to the file to read.

        Returns:
            str: Content of the file or error message.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return "[File not found]"
        except PermissionError:
            logger.error(f"Permission denied accessing file: {file_path}")
            return "[Permission denied]"
        except UnicodeDecodeError:
            logger.warning(f"Binary file detected: {file_path}")
            return "[Binary file content not shown]"
        except IOError as e:
            logger.error(f"I/O error reading file {file_path}: {str(e)}")
            return f"[I/O error: {str(e)}]"
        except Exception as e:
            logger.error(
                f"Unexpected error reading file {file_path}: {str(e)}"
            )
            logger.debug("Stack trace:", exc_info=True)
            return f"[Unexpected error: {str(e)}]"

    def collect_code(
        self,
        input_paths: Union[str, List[str]],
        title: str = "Code Collection",
    ) -> Optional[Path]:
        """Process all files and generate markdown documentation.

        Args:
            input_paths: Path(s) to process.
            title: Title for the collection.

        Returns:
            Optional[Path]: Path to generated markdown file or None if failed.
            The path is returned as a Path object if successful,
            None if failed.
        """
        try:
            all_files = self.collect_files(input_paths)
            if not all_files:
                logger.warning("No files found to process")
                return None

            # Create output files with timestamp and path info
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Convert input paths to string
            if isinstance(input_paths, str):
                path_str = input_paths
            else:
                path_str = "_".join(input_paths)
            # Clean up path string
            path_str = path_str.replace("/", "_").replace(".", "_")

            code_output_path = self.storage.get_output_path(
                f"FULL_CODE_{timestamp}_{path_str}_{title}.md"
            )

            # Create the code collection file
            import os

            # Create parent directory if it doesn't exist
            code_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Force sync parent directory
            os.sync()

            with open(code_output_path, "w", encoding="utf-8") as output_file:
                # Write header
                output_file.write(f"# {title}\n\n")
                output_file.write(
                    "This file contains code from the specified paths, "
                    "organized by file path.\n\n"
                )

                # Write table of contents
                output_file.write("## Table of Contents\n\n")
                for file_path in all_files:
                    try:
                        relative_path = file_path.relative_to(
                            self.project_root
                        )
                    except ValueError:
                        relative_path = file_path
                    anchor = self.make_anchor(relative_path)
                    output_file.write(f"- [{relative_path}](#{anchor})\n")

                # Write file contents
                output_file.write("\n## Files\n\n")
                for file_path in all_files:
                    try:
                        relative_path = file_path.relative_to(
                            self.project_root
                        )
                    except ValueError:
                        relative_path = file_path

                    content = self.read_file_content(file_path)
                    anchor = self.make_anchor(relative_path)
                    lang = LanguageMap.get_language(file_path)

                    output_file.write(f"### {relative_path} {{{anchor}}}\n")
                    output_file.write(f"```{lang}\n{content}\n```\n\n")
                    logger.info(f"Processed: {relative_path}")

                # Force sync code file
                output_file.flush()
                os.fsync(output_file.fileno())

            # Create analysis prompt file with timestamp
            analyze_output_path = self.storage.get_output_path(
                f"PROMPT_ANALYZE_{timestamp}_{path_str}_{title}.md"
            )
            prompt_path = (
                Path(__file__).parent / "prompts" / "analyze.prompt.md"
            )

            # Read code content first
            code_content = self.read_file_content(code_output_path)
            prompt_content = self.read_file_content(prompt_path)

            # Create parent directory if it doesn't exist
            analyze_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Force sync parent directory
            os.sync()

            # Then write analysis file
            with open(
                analyze_output_path, "w", encoding="utf-8"
            ) as analyze_file:
                analyze_file.write(prompt_content)
                analyze_file.write("\n")
                analyze_file.write(code_content)
                # Force sync analysis file
                analyze_file.flush()
                os.fsync(analyze_file.fileno())

            # Final sync to ensure all writes are complete
            os.sync()

            # Verify files exist and are accessible
            if not code_output_path.exists():
                raise RuntimeError(
                    f"Failed to create code file: {code_output_path}"
                )
            if not analyze_output_path.exists():
                raise RuntimeError(
                    f"Failed to create analysis file: {analyze_output_path}"
                )

            # Force final sync
            os.sync()

            logger.info(f"Analysis prompt created: {analyze_output_path}")
            logger.info(
                f"Code collection complete! Created: {code_output_path}"
            )
            return Path(code_output_path)

        except FileNotFoundError as e:
            logger.error(f"File not found error: {str(e)}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied error: {str(e)}")
            return None
        except OSError as e:
            logger.error(f"OS error during code collection: {str(e)}")
            return None
        except RuntimeError as e:
            logger.error(f"Runtime error during code collection: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during code collection: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            return None
