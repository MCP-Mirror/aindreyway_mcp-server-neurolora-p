"""Code collection functionality."""

import fnmatch
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..file_naming import FileType, format_filename, get_file_pattern
from ..storage import StorageManager
from ..log_utils import get_logger, LogCategory

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
        self.ignore_patterns = self.load_ignore_patterns()

    def load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .neuroloraignore file.

        Returns:
            List[str]: List of ignore patterns
        """
        # First check for user's .neuroloraignore
        ignore_file = self.project_root / ".neuroloraignore"
        logger.debug(f"Looking for ignore file at: {ignore_file}")

        patterns: List[str] = []
        try:
            if ignore_file.exists():
                with open(ignore_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith("#"):
                            patterns.append(line)
                logger.debug(f"Loaded {len(patterns)} ignore patterns")
            else:
                logger.debug("No .neuroloraignore found, using empty patterns")
        except FileNotFoundError:
            logger.warning("Could not find .neuroloraignore file")
        except PermissionError:
            logger.error("Permission denied accessing .neuroloraignore")
        except UnicodeDecodeError:
            logger.error("Invalid file encoding in .neuroloraignore")
        except OSError as e:
            logger.error(f"System error loading .neuroloraignore: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid pattern in .neuroloraignore: {str(e)}")

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
        except ValueError:
            relative_path = file_path

        str_path = str(relative_path)

        # Check each ignore pattern
        for pattern in self.ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                if any(part == pattern[:-1] for part in relative_path.parts):
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(
                file_path.name, pattern
            ):
                return True

        # Check for generated files using new naming patterns
        for file_type in FileType:
            if get_file_pattern(file_type).match(str(file_path)):
                return True

        # Always ignore .neuroloraignore files
        if file_path.name == ".neuroloraignore":
            return True

        try:
            # Handle large files (> 1MB)
            MAX_SIZE = 1024 * 1024  # 1MB
            if file_path.exists() and file_path.stat().st_size > MAX_SIZE:
                return False
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Error checking file size for {str_path}: {str(e)}")
            return True
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

        for input_path in input_paths:
            try:
                # Convert relative path to absolute using project_root
                path = Path(input_path)
                if not path.is_absolute():
                    path = (self.project_root / path).resolve()
                else:
                    path = path.resolve()
            except (ValueError, RuntimeError) as e:
                logger.error(f"Invalid path format {input_path}: {str(e)}")
                continue

            try:
                if not path.exists():
                    logger.error(f"Path does not exist: {path}")
                    continue
            except OSError as e:
                logger.error(
                    f"System error accessing path {input_path}: {str(e)}"
                )
                continue

            if path.is_file():
                if not self.should_ignore_file(path):
                    all_files.append(path)
            else:
                for root, dirs, files in os.walk(path):
                    root_path = Path(root)
                    # Remove ignored directories in-place
                    dirs[:] = [
                        d
                        for d in dirs
                        if not self.should_ignore_file(root_path / d)
                    ]

                    for file in sorted(files):
                        file_path = root_path / file
                        if not self.should_ignore_file(file_path):
                            all_files.append(file_path)

        from typing import Tuple

        # Sort files with PROJECT_SUMMARY.md first
        def sort_key(path: Path) -> Tuple[int, str]:
            try:
                relative_path = path.relative_to(self.project_root)
            except ValueError:
                relative_path = path
            # Sort order: PROJECT_SUMMARY.md first,
            # then alphabetically
            is_summary = relative_path.name == "PROJECT_SUMMARY.md"
            return (0 if is_summary else 1, str(relative_path))

        return sorted(all_files, key=sort_key)

    def read_file_content(self, file_path: Path) -> str:
        """Read content of a file with proper encoding handling.

        Args:
            file_path: Path to the file to read.

        Returns:
            str: Content of the file or error message.
        """
        try:
            file_size = file_path.stat().st_size
            MAX_SIZE = 1024 * 1024  # 1MB
            PREVIEW_SIZE = 64 * 1024  # 64KB

            with open(file_path, "r", encoding="utf-8") as f:
                if file_size > MAX_SIZE:
                    content = f.read(PREVIEW_SIZE)
                    return (
                        f"{content}\n\n"
                        "[File truncated, showing first "
                        f"{PREVIEW_SIZE // 1024}KB of "
                        f"{file_size // 1024}KB]"
                    )
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
        except OSError as e:
            logger.error(f"System error reading file {file_path}: {str(e)}")
            return f"[System error: {str(e)}]"
        except ValueError as e:
            logger.error(f"Invalid file format {file_path}: {str(e)}")
            return f"[Invalid format: {str(e)}]"

    def collect_code(
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
            all_files = self.collect_files(input_paths)
            if not all_files:
                logger.warning("No files found to process")
                return None

            # Create output files with new naming scheme
            code_output_path = self.storage.get_output_path(
                format_filename(FileType.CODE)
            )

            # Create parent directory if it doesn't exist
            code_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write code collection file
            with open(code_output_path, "w", encoding="utf-8") as output_file:
                # Write header
                output_file.write("# Code Collection\n\n")
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
                    logger.debug(f"Processed file: {relative_path}")

                # Ensure file is written
                output_file.flush()

            # Create analysis prompt file with new naming scheme
            analyze_output_path = self.storage.get_output_path(
                format_filename(FileType.IMPROVE_PROMPT)
            )
            prompt_path = (
                Path(__file__).parent.parent / "prompts" / "improve.prompt.md"
            )

            # Read code content first
            code_content = self.read_file_content(code_output_path)
            prompt_content = self.read_file_content(prompt_path)

            # Write analysis file
            with open(
                analyze_output_path, "w", encoding="utf-8"
            ) as analyze_file:
                analyze_file.write(prompt_content)
                analyze_file.write("\n")
                analyze_file.write(code_content)
                # Ensure file is written
                analyze_file.flush()

            # Verify files exist and are accessible
            if not code_output_path.exists():
                raise RuntimeError(
                    f"Failed to create code file: {code_output_path}"
                )
            if not analyze_output_path.exists():
                raise RuntimeError(
                    f"Failed to create analysis file: {analyze_output_path}"
                )

            # Calculate approximate token count
            # Using rough estimate: 4 chars per token
            code_content = self.read_file_content(code_output_path)
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
