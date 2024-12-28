"""Base class for AI-powered code analysis."""

import logging
import os
from pathlib import Path
from typing import Optional

from ..file_naming import FileType, format_filename
from ..storage import StorageManager
from ..types import Context
from .collector import Collector

# Get module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BaseAnalyzer:
    """Base class for AI-powered code analysis tools."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        context: Optional["Context"] = None,
    ) -> None:
        """Initialize the analyzer.

        Args:
            project_root: Optional path to project root directory.
                        If not provided, uses current working directory.
        """
        # Get the project root directory
        self.project_root = project_root or Path.cwd()

        # Initialize storage manager
        self.storage = StorageManager(project_root)
        self.storage.setup()

        # Initialize code collector
        self.collector = Collector(project_root)

        # Store context for progress reporting
        self.context = context

        # Initialize AI provider using factory
        from ..providers import create_provider

        logger.info("Creating AI provider")
        self.provider = create_provider()
        logger.info("AI provider created")

    async def analyze_code(
        self,
        input_paths: str | list[str],
        title: str,
        prompt_name: str,
        output_type: FileType,
        extra_content: str = "",
    ) -> Optional[Path]:
        """Analyze code using AI.

        Args:
            input_paths: Path(s) to analyze
            title: Title for the collection
            prompt_name: Name of the prompt file (without .prompt.md)
            output_type: Type of output file
            extra_content: Additional content to add to prompt

        Returns:
            Optional[Path]: Path to generated analysis file or None if failed
        """
        try:
            if self.context:
                self.context.info("Starting code collection...")

            # First collect all code
            code_file = self.collector.collect_code(input_paths)
            if not code_file:
                logger.error("Failed to collect code")
                return None

            if self.context:
                self.context.info("Code collected successfully")
                await self.context.report_progress(25, 100)

            # Read the collected code
            code_content = self.collector.read_file_content(code_file)

            if self.context:
                self.context.info("Getting analysis prompt...")
                await self.context.report_progress(50, 100)

            # Get prompt
            prompt_path = (
                Path(__file__).parent.parent
                / "prompts"
                / f"{prompt_name}.prompt.md"
            )
            prompt_content = self.collector.read_file_content(prompt_path)

            # Combine prompt and code
            full_prompt = (
                f"{prompt_content}\n\n{extra_content}\n\n{code_content}"
            )

            # Get AI analysis
            try:
                if self.context:
                    model = os.getenv("AI_MODEL", "unknown")
                    provider = self.provider.name
                    self.context.info(
                        f"Starting analysis with model: {model} ({provider})"
                    )
                    await self.context.report_progress(75, 100)

                analysis = await self.provider.analyze(full_prompt)
            except ValueError as e:
                logger.error("Invalid input for analysis: %s", str(e))
                return None
            except RuntimeError as e:
                logger.error("Analysis failed: %s", str(e))
                return None

            # Use same timestamp for all files
            from datetime import datetime

            timestamp = datetime.now()

            # Create output paths with same timestamp
            code_output_path = self.storage.get_output_path(
                format_filename(
                    FileType.CODE,
                    prompt_name,
                    timestamp=timestamp,
                    provider=self.provider.name,
                )
            )

            # Save collected code
            with open(code_output_path, "w", encoding="utf-8") as f:
                f.write(code_content)
                f.flush()

            # Save prompt based on command
            prompt_type = (
                FileType.REQUEST_PROMPT
                if output_type == FileType.REQUEST_RESULT
                else FileType.IMPROVE_PROMPT
            )
            prompt_output_path = self.storage.get_output_path(
                format_filename(
                    prompt_type,
                    prompt_name,
                    timestamp=timestamp,
                    provider=self.provider.name,
                )
            )
            with open(prompt_output_path, "w", encoding="utf-8") as f:
                f.write(full_prompt)
                f.flush()

            # Write analysis result only for improve and request commands
            if output_type in [
                FileType.IMPROVE_RESULT,
                FileType.REQUEST_RESULT,
            ]:
                result_output_path = self.storage.get_output_path(
                    format_filename(
                        output_type,
                        prompt_name,
                        timestamp=timestamp,
                        provider=self.provider.name,
                    )
                )
                with open(result_output_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n")
                    if extra_content:
                        f.write(f"{extra_content}\n\n")
                    f.write(f"Analysis of code from: {input_paths}\n")
                    f.write(f"Model: {os.getenv('AI_MODEL', 'o1')}\n\n")
                    f.write(analysis)
                    f.flush()
                if self.context:
                    self.context.info("Analysis complete!")
                    await self.context.report_progress(100, 100)
                return Path(result_output_path)

            if self.context:
                self.context.info("Analysis complete!")
                await self.context.report_progress(100, 100)
            return Path(code_output_path)

        except (ValueError, TypeError) as e:
            logger.error("Invalid input error: %s", str(e))
            return None
        except OSError as e:
            logger.error("System error: %s", str(e))
            return None
        except RuntimeError as e:
            logger.error("Runtime error: %s", str(e))
            return None
