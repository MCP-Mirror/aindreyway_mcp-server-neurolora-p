"""Base class for code analysis tools."""

import os
from pathlib import Path
from typing import List, Optional, Union

from ..file_naming import FileType, format_filename
from ..log_utils import LogCategory, get_logger
from ..providers import create_provider
from ..storage import StorageManager
from ..types import Context
from ..utils import async_io
from .collector import Collector

# Get module logger
logger = get_logger(__name__, LogCategory.TOOLS)


class BaseAnalyzer:
    """Base class for code analysis tools."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        context: Optional[Context] = None,
    ) -> None:
        """Initialize the analyzer.

        Args:
            project_root: Optional path to project root directory.
                        If not provided, uses current working directory.
            context: Optional context for progress reporting.
        """
        # Get the project root directory
        self.project_root = project_root or Path.cwd()

        # Initialize storage manager
        self.storage = StorageManager(project_root)
        try:
            self.storage.setup()
            logger.info("Storage setup completed successfully")
        except Exception as err:
            logger.error("Failed to setup storage: %s", str(err))
            raise RuntimeError(f"Storage setup failed: {str(err)}")

        # Initialize code collector
        self.collector = Collector(project_root)

        # Initialize AI provider
        self.provider = create_provider()

        # Store context for progress reporting
        self.context = context

    async def analyze_code(
        self,
        input_paths: Union[str, List[str]],
        title: str,
        prompt_name: str,
        output_type: FileType,
        extra_content: str = "",
    ) -> Optional[Path]:
        """Analyze code and generate report.

        Args:
            input_paths: Path(s) to analyze
            title: Title for analysis report
            prompt_name: Name of prompt file to use
            output_type: Type of output file to generate
            extra_content: Optional extra content to add to prompt

        Returns:
            Optional[Path]: Path to generated analysis file or None if failed
        """
        try:
            # Input validation
            if not input_paths:
                logger.error("Empty input path")
                return None

            # Convert input paths to list of strings
            validated_paths: List[str]
            if isinstance(input_paths, list):
                # Filter out empty paths and convert to strings
                validated_paths = [str(p) for p in input_paths if p]
                if not validated_paths:
                    logger.error("No valid paths in list")
                    return None
            else:
                validated_paths = [str(input_paths)]

            # Report progress
            if self.context:
                self.context.info("Starting code collection...")
                await self.context.report_progress(0.25, 100.0)

            # Collect code
            code_output = await self.collector.collect_code(validated_paths)
            if not code_output:
                logger.error("Code collection failed or no files found")
                return None

            if self.context:
                self.context.info("Code collected successfully")
                await self.context.report_progress(0.50, 100.0)

            # Read code content and write to file
            code_content = await async_io.read_file(code_output)
            await async_io.write_file(code_output, code_content)

            # Read prompt template and write to file
            prompt_path = (
                Path(__file__).parent.parent / "prompts" / f"{prompt_name}.prompt.md"
            )
            prompt_content = await async_io.read_file(prompt_path)
            await async_io.write_file(prompt_path, prompt_content)

            # Prepare analysis content
            analysis_content = f"{prompt_content}\n\n{extra_content}\n\n{code_content}"

            # Get analysis from AI provider
            if self.context:
                await self.context.report_progress(0.75, 100.0)

            analysis_result = await self.provider.analyze(analysis_content)

            # Create output file
            output_path = self.storage.get_output_path(format_filename(output_type))

            # Format result with metadata
            model_info = os.getenv("AI_MODEL", "default")
            formatted_result = (
                f"# {title}\n\n"
                f"Model: {model_info}\n\n"
                f"{analysis_result or 'No analysis results available.'}"
            )

            # Write result
            await async_io.write_file(output_path, formatted_result)

            if self.context:
                self.context.info("Analysis complete!")
                await self.context.report_progress(1.0, 100.0)

            return output_path

        except Exception as err:
            logger.error("Error during analysis: %s", str(err))
            return None
