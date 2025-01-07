"""Storage management functionality.

This module handles the storage structure and symlinks for the
Neurolora project.
"""

import os
from pathlib import Path
from typing import Optional

try:
    import appdirs
except ImportError:
    raise RuntimeError(
        "appdirs package is required.\n" "Please install it with: pip install appdirs"
    )

from .log_utils import LogCategory, get_logger
from .utils import file_lock, sanitize_filename, validate_path

# Get module logger
logger = get_logger(__name__, LogCategory.STORAGE)

# Application specific constants
APP_NAME = "mcp"
APP_AUTHOR = "modelcontextprotocol"


class StorageManager:
    """Manages storage directories and symlinks for Neurolora."""

    project_root: Path
    project_name: str
    mcp_docs_dir: Path
    project_docs_dir: Path
    neurolora_link: Path

    def __init__(
        self,
        project_root: Optional[Path] = None,
        subproject_id: Optional[str] = None,
    ) -> None:
        """Initialize the StorageManager.

        Args:
            project_root: Optional path to project root directory.
                        If not provided, uses current working directory.
            subproject_id: Optional subproject identifier.
                        If provided, will be appended to project name.
        """
        self.project_root = validate_path(project_root) if project_root else Path.cwd()

        # Get project name and handle subproject
        base_name = self.project_root.name
        if subproject_id:
            subproject_id = sanitize_filename(subproject_id)
            self.project_name = f"{base_name}-{subproject_id}"
        else:
            self.project_name = base_name

        # Get platform-specific user data directory:
        # - macOS: ~/Library/Application Support/mcp/.mcp-docs
        # - Linux: ~/.local/share/mcp/.mcp-docs
        # - Windows: %APPDATA%/modelcontextprotocol/mcp/.mcp-docs
        data_dir = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
        self.mcp_docs_dir = Path(data_dir) / ".mcp-docs"
        try:
            self.mcp_docs_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Using platform data directory: %s", self.mcp_docs_dir)
        except (PermissionError, OSError) as err:
            logger.error(
                "Failed to create data directory: %s\n"
                "Please check directory permissions and disk space.",
                str(err),
            )
            raise RuntimeError(f"Failed to create data directory: {str(err)}")

        # Setup project paths
        self.project_docs_dir = self.mcp_docs_dir / self.project_name
        self.neurolora_link = self.project_root / ".neurolora"

        logger.info(
            "Storage manager initialized with docs directory: %s",
            self.mcp_docs_dir,
        )

    def setup(self) -> None:
        """Setup storage structure and symlinks."""
        # Create all required directories immediately
        self._create_directories()

        # Create symlink and required files
        self._create_symlinks()
        self._create_ignore_file()
        self._create_task_files()

        # Ensure the project directory exists and is ready
        logger.info(
            "Storage setup complete. Project directory: %s",
            self.project_docs_dir,
        )

    def _create_directories(self) -> None:
        """Create required directories."""
        try:
            # Create all required directories
            self.mcp_docs_dir.mkdir(parents=True, exist_ok=True)
            self.project_docs_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Created/verified project directory: %s",
                self.project_docs_dir,
            )

            # Create marker file and force immediate directory availability
            marker = self.project_docs_dir / ".initialized"
            with file_lock(marker):
                with open(marker, "w") as f:
                    f.write("initialized")
                    f.flush()
                    os.fsync(f.fileno())

            # Verify directory exists and is accessible
            if not self.project_docs_dir.exists():
                raise RuntimeError(
                    f"Failed to create directory: {self.project_docs_dir}"
                )
        except PermissionError as err:
            logger.error(
                "Permission denied creating directories: %s\n"
                "Please check directory permissions.",
                str(err),
            )
            raise
        except OSError as err:
            logger.error(
                "System error creating directories: %s\n"
                "This may indicate disk space or I/O issues.",
                str(err),
            )
            raise
        except (TypeError, ValueError) as err:
            logger.error(
                "Invalid path or filename: %s\n"
                "Please check path components are valid.",
                str(err),
            )
            raise

    def _create_symlinks(self) -> None:
        """Create or update symlinks."""
        try:
            # Create symlink from project root to project docs directory
            self._create_or_update_symlink(
                self.neurolora_link,
                self.project_docs_dir,
                ".neurolora",
            )
            # Verify symlink is created and valid
            if not self.neurolora_link.exists() or not self.neurolora_link.is_symlink():
                raise RuntimeError(f"Failed to create symlink: {self.neurolora_link}")

            logger.info(
                "Symlink created and verified: %s",
                self.neurolora_link,
            )
        except PermissionError as err:
            logger.error(
                "Permission denied creating symlink: %s\n"
                "Please check file permissions.",
                str(err),
            )
            raise
        except OSError as err:
            logger.error(
                "System error creating symlink: %s\n"
                "This may indicate filesystem limitations.",
                str(err),
            )
            raise
        except (TypeError, ValueError) as err:
            logger.error(
                "Invalid path for symlink: %s\n"
                "Please check path components are valid.",
                str(err),
            )
            raise

    def _create_or_update_symlink(
        self, link_path: Path, target_path: Path, link_name: str
    ) -> None:
        """Create or update a symlink.

        Args:
            link_path: Path where symlink should be created
            target_path: Path that symlink should point to
            link_name: Name of the symlink for logging
        """
        try:
            # Convert to Path objects if needed
            link_path = Path(link_path)
            target_path = Path(target_path)
            logger.debug("Using paths:")
            logger.debug("  link_path: %s", link_path)
            logger.debug("  target_path: %s", target_path)

            # Ensure target directory exists
            target_path.mkdir(parents=True, exist_ok=True)

            # Create relative symlink
            relative_target = os.path.relpath(target_path.resolve(), link_path.parent)
            logger.debug(
                "Creating symlink: %s -> %s (relative: %s)",
                link_path,
                target_path,
                relative_target,
            )

            if link_path.exists():
                if not link_path.is_symlink():
                    logger.warning("Removing non-symlink %s", link_name)
                    link_path.unlink()
                    link_path.symlink_to(relative_target, target_is_directory=True)
                elif link_path.resolve() != target_path:
                    logger.warning("Updating incorrect %s symlink", link_name)
                    link_path.unlink()
                    link_path.symlink_to(relative_target, target_is_directory=True)
            else:
                link_path.symlink_to(relative_target, target_is_directory=True)

            # Verify symlink
            if not link_path.exists():
                raise RuntimeError(f"Symlink was not created: {link_path}")
            if not link_path.is_symlink():
                raise RuntimeError(f"Path exists but is not a symlink: {link_path}")
            resolved = link_path.resolve()
            if resolved != target_path:
                msg = f"Symlink points to wrong target: " f"{resolved} != {target_path}"
                raise RuntimeError(msg)

        except PermissionError as err:
            logger.error(
                "Permission denied managing symlink: %s\n"
                "Please check file permissions.",
                str(err),
            )
            raise
        except OSError as err:
            logger.error(
                "System error managing symlink: %s\n"
                "This may indicate filesystem limitations.",
                str(err),
            )
            raise
        except (TypeError, ValueError) as err:
            logger.error(
                "Invalid path for symlink operation: %s\n"
                "Please check path components are valid.",
                str(err),
            )
            raise

    def _create_template_file(
        self,
        template_name: str,
        output_name: str,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Create a file from a template if it doesn't exist.

        Args:
            template_name: Name of the template file
            output_name: Name of the output file
            output_dir: Optional directory for output file.
                       If not provided, uses project_docs_dir.
        """
        try:
            # Validate and sanitize inputs
            template_name = sanitize_filename(template_name)
            output_name = sanitize_filename(output_name)
            if output_dir:
                output_dir = validate_path(output_dir)

            output_file = (output_dir or self.project_docs_dir) / output_name
            if not output_file.exists():
                # Copy from template
                template_file = Path(__file__).parent / "templates" / template_name
                if template_file.exists():
                    try:
                        with file_lock(output_file):
                            # Read template content first
                            with open(template_file, "r", encoding="utf-8") as src:
                                content = src.read()
                            # Then write to output file
                            with open(output_file, "w", encoding="utf-8") as dst:
                                dst.write(content)
                    except PermissionError:
                        logger.error(
                            "Permission denied accessing files: "
                            f"{output_file} or {template_file}\n"
                            "Please check file permissions."
                        )
                        raise
                    except UnicodeDecodeError:
                        logger.error(
                            "Invalid file encoding in template: "
                            f"{template_file}\n"
                            "Please ensure template files are UTF-8 encoded."
                        )
                        raise
                    except IOError as err:
                        logger.error(
                            "I/O error with files: %s\n"
                            "This may indicate disk or system issues.",
                            str(err),
                        )
                        raise
                else:
                    logger.warning("Template file not found: %s", template_file)
        except (TypeError, ValueError) as err:
            logger.error(
                "Invalid filename or path: %s\n"
                "Please ensure filenames contain valid characters.",
                str(err),
            )
            raise
        except OSError as err:
            if isinstance(err, PermissionError):
                logger.error(
                    "Permission denied: %s\n" "Please check file permissions.",
                    str(err),
                )
            elif isinstance(err, UnicodeDecodeError):
                logger.error(
                    "Invalid file encoding: %s\n"
                    "Please ensure files are UTF-8 encoded.",
                    str(err),
                )
            else:
                logger.error(
                    "Operating system error: %s\n"
                    "This may indicate disk or system issues.",
                    str(err),
                )
            raise

    def _create_ignore_file(self) -> None:
        """Create .neuroloraignore file if it doesn't exist."""
        self._create_template_file(
            "ignore.template", ".neuroloraignore", self.project_root
        )

    def _create_task_files(self) -> None:
        """Create TODO.md and DONE.md files if they don't exist."""
        self._create_template_file("todo.template.md", "TODO.md")
        self._create_template_file("done.template.md", "DONE.md")

    def get_output_path(self, filename: str) -> Path:
        """Get path for output file in project docs directory.

        Args:
            filename: Name of the file

        Returns:
            Path: Full path in project docs directory
        """
        # Sanitize filename before using it
        safe_name = sanitize_filename(filename)
        return self.project_docs_dir / safe_name
