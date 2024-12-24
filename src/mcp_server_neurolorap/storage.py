"""Storage management functionality.

This module handles the storage structure and symlinks for the
Neurolora project.
"""

import logging
from pathlib import Path
from typing import Optional

# Get module logger
logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage directories and symlinks for Neurolora."""

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
        self.project_root = project_root or Path.cwd()
        logger.info("Initializing storage manager")
        logger.debug("Project root: %s", self.project_root)

        # Get project name and handle subproject
        base_name = self.project_root.name
        if subproject_id:
            self.project_name = f"{base_name}-{subproject_id}"
            self.neurolora_link = (
                self.project_root / f".neurolora_{subproject_id}"
            )
        else:
            self.project_name = base_name
            self.neurolora_link = self.project_root / ".neurolora"

        # Setup paths
        self.mcp_docs_dir = Path.home() / ".mcp-docs"
        self.project_docs_dir = self.mcp_docs_dir / self.project_name

        logger.debug("Project name: %s", self.project_name)
        logger.debug("Project docs dir: %s", self.project_docs_dir)
        logger.debug("Neurolora link: %s", self.neurolora_link)
        logger.info("Storage manager initialized")

    def setup(self) -> None:
        """Setup storage structure and symlinks."""
        # Create all required directories immediately
        self._create_directories()

        # Create symlink and ignore file
        self._create_symlinks()
        self._create_ignore_file()

        # Ensure the project directory exists and is ready
        logger.info(
            "Storage setup complete. Project directory: %s",
            self.project_docs_dir,
        )

    def _create_directories(self) -> None:
        """Create required directories."""
        try:
            # Create all directories with parents
            try:
                self.project_docs_dir.mkdir(parents=True, exist_ok=True)
                logger.info(
                    "Created/verified project directory: %s",
                    self.project_docs_dir,
                )
            except PermissionError:
                logger.error(
                    f"Permission denied creating directory: "
                    f"{self.project_docs_dir}"
                )
                raise
            except OSError as e:
                logger.error(f"OS error creating directory: {str(e)}")
                raise

            # Verify directory exists and is accessible
            if not self.project_docs_dir.exists():
                raise RuntimeError(
                    f"Failed to create directory: {self.project_docs_dir}"
                )

            # Create marker file to indicate initialization
            marker = self.project_docs_dir / ".initialized"
            try:
                with open(marker, "w") as f:
                    f.write("initialized")
            except PermissionError:
                logger.error(
                    f"Permission denied creating marker file: {marker}"
                )
                raise
            except IOError as e:
                logger.error(f"I/O error creating marker file: {str(e)}")
                raise

        except (PermissionError, OSError, IOError) as e:
            logger.error(f"File system error creating directories: {str(e)}")
            raise
        except RuntimeError as e:
            logger.error(f"Runtime error creating directories: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating directories: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            raise

    def _create_symlinks(self) -> None:
        """Create or update symlinks."""
        try:
            # Create symlink to project docs directory
            self._create_or_update_symlink(
                self.neurolora_link,
                self.project_docs_dir,
                ".neurolora",
            )

            # Verify symlink was created successfully
            if not self.neurolora_link.exists():
                raise RuntimeError(
                    f"Failed to create symlink: {self.neurolora_link}"
                )
            if not self.neurolora_link.is_symlink():
                raise RuntimeError(
                    f"Path exists but is not a symlink: {self.neurolora_link}"
                )

            logger.info(
                "Symlink created and verified: %s",
                self.neurolora_link,
            )
        except (PermissionError, OSError) as e:
            logger.error(f"File system error creating symlinks: {str(e)}")
            raise
        except RuntimeError as e:
            logger.error(f"Runtime error creating symlinks: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating symlinks: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
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
        logger.debug(
            "Creating symlink: %s -> %s",
            link_path,
            target_path,
        )
        try:
            try:
                if link_path.exists():
                    logger.debug("Link path exists: %s", link_path)
                    if not link_path.is_symlink():
                        logger.warning("Removing non-symlink %s", link_name)
                        link_path.unlink()
                        link_path.symlink_to(
                            target_path, target_is_directory=True
                        )
                    elif link_path.resolve() != target_path:
                        logger.warning(
                            "Updating incorrect %s symlink", link_name
                        )
                        link_path.unlink()
                        link_path.symlink_to(
                            target_path, target_is_directory=True
                        )
                else:
                    logger.debug("Creating new symlink")
                    link_path.symlink_to(target_path, target_is_directory=True)
                    logger.debug("Created %s symlink", link_name)
            except PermissionError as e:
                logger.error(
                    f"Permission denied manipulating symlink: {str(e)}"
                )
                raise
            except FileNotFoundError as e:
                logger.error(f"Path not found: {str(e)}")
                raise
            except OSError as e:
                logger.error(f"OS error manipulating symlink: {str(e)}")
                raise

            # Verify symlink
            try:
                if not link_path.exists():
                    raise RuntimeError(f"Symlink was not created: {link_path}")
                if not link_path.is_symlink():
                    raise RuntimeError(
                        f"Path exists but is not a symlink: {link_path}"
                    )
                resolved = link_path.resolve()
                if resolved != target_path:
                    msg = (
                        f"Symlink points to wrong target: "
                        f"{resolved} != {target_path}"
                    )
                    raise RuntimeError(msg)
                logger.debug("Symlink verified successfully")
            except RuntimeError:
                raise
            except OSError as e:
                logger.error(f"Error verifying symlink: {str(e)}")
                raise

        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.error(f"File system error creating symlink: {str(e)}")
            raise
        except RuntimeError as e:
            logger.error(f"Runtime error creating symlink: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating symlink: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            raise

    def _create_ignore_file(self) -> None:
        """Create .neuroloraignore file if it doesn't exist."""
        try:
            ignore_file = self.project_root / ".neuroloraignore"
            if not ignore_file.exists():
                # Copy default ignore patterns
                default_ignore = (
                    Path(__file__).parent / "default.neuroloraignore"
                )
                if default_ignore.exists():
                    try:
                        with open(
                            default_ignore, "r", encoding="utf-8"
                        ) as src:
                            content = src.read()
                        with open(ignore_file, "w", encoding="utf-8") as dst:
                            dst.write(content)
                        logger.debug(
                            "Created .neuroloraignore from default template"
                        )
                    except PermissionError:
                        logger.error(
                            f"Permission denied accessing ignore files: "
                            f"{ignore_file} or {default_ignore}"
                        )
                        raise
                    except UnicodeDecodeError:
                        logger.error(
                            f"Invalid file encoding in template: "
                            f"{default_ignore}"
                        )
                        raise
                    except IOError as e:
                        logger.error(f"I/O error with ignore files: {str(e)}")
                        raise
                else:
                    logger.warning(
                        "Default .neuroloraignore template not found"
                    )
        except (PermissionError, UnicodeDecodeError, IOError) as e:
            logger.error(f"File system error with ignore files: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error with ignore files: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            raise

    def get_output_path(self, filename: str) -> Path:
        """Get path for output file in project docs directory.

        Args:
            filename: Name of the file

        Returns:
            Path: Full path in project docs directory
        """
        return self.project_docs_dir / filename
