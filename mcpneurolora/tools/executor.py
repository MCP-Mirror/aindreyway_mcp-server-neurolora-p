"""Tool execution logic shared between MCP server and terminal."""

from pathlib import Path
from typing import Any, Optional

from ..types import Context

from ..tools import Collector, Reporter
from ..tools.improver import Improver
from ..tools.requester import Requester
from ..logging import get_logger, LogCategory
from ..utils.progress import ProgressTracker

# Get module logger
logger = get_logger(__name__, LogCategory.TOOLS)


class ToolExecutor:
    """Executes tools with shared logic between MCP server and terminal."""

    def __init__(
        self,
        project_root: Optional[Path | str] = None,
        context: Optional[Context] = None,
    ) -> None:
        """Initialize tool executor.

        Args:
            project_root: Optional root directory for code collection
            context: Optional MCP Context for progress reporting
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.context = context

    async def execute_code_collector(
        self,
        input_path: str | list[str] = ".",
    ) -> str:
        """Execute code collection tool.

        Args:
            input_path: Path or list of paths to collect code from

        Returns:
            Path to the output file or error message
        """
        try:
            collector = Collector(project_root=self.project_root)
            logger.info("Starting code collection")

            output_file = collector.collect_code(input_path)
            if not output_file:
                logger.error("No files found to process")
                return "No files found to process"

            logger.info("Code collection complete: %s", output_file)
            return str(output_file)

        except Exception as e:
            logger.error("Error during code collection: %s", str(e))
            return f"Error during code collection: {str(e)}"

    async def execute_project_structure_reporter(
        self,
        output_filename: str = "FULL_TREE_PROJECT_FILES.md",
    ) -> str:
        """Execute project structure reporter tool.

        Args:
            output_filename: Name for the output report file

        Returns:
            Path to the output file or error message
        """
        try:
            reporter = Reporter(root_dir=self.project_root)
            logger.info("Starting project structure analysis")

            report_data = reporter.analyze_project_structure()
            output_path = self.project_root / ".neurolora" / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            reporter.generate_markdown_report(report_data, output_path)
            logger.info("Project structure report generated: %s", output_path)
            return str(output_path)

        except Exception as e:
            logger.error("Error during report generation: %s", str(e))
            return f"Error during report generation: {str(e)}"

    async def execute_improve(
        self,
        input_path: str | list[str] = ".",
    ) -> str:
        """Execute improve tool.

        Args:
            input_path: Path or list of paths to analyze

        Returns:
            Path to the output file or error message
        """
        try:
            improver = Improver(project_root=self.project_root)
            logger.info("Starting code analysis")

            progress = ProgressTracker(
                total_steps=100,
                prefix="[AI Analysis]",
            )
            await progress.start()

            try:
                output_file = await improver.improve(input_path)
                if not output_file:
                    msg = "Failed to analyze code"
                    logger.error(msg)
                    await progress.stop("Error: Analysis failed")
                    return msg

                await progress.stop("Analysis complete")
                logger.info("Code analysis complete: %s", output_file)
                return str(output_file)

            except Exception as e:
                logger.error("Error during code analysis: %s", str(e))
                await progress.stop("Error: Analysis failed")
                return f"Error during code analysis: {str(e)}"

        except Exception as e:
            logger.error("Error during code analysis: %s", str(e))
            return f"Error during code analysis: {str(e)}"

    async def execute_request(
        self,
        input_path: str | list[str] = ".",
        request_text: str = "",
    ) -> str:
        """Execute request tool.

        Args:
            input_path: Path or list of paths to analyze
            request_text: User's request text

        Returns:
            Path to the output file or error message
        """
        if not request_text:
            return "Request text is required"

        try:
            requester = Requester(project_root=self.project_root)
            logger.info("Starting request analysis")

            progress = ProgressTracker(
                total_steps=100,
                prefix="[AI Analysis]",
            )
            await progress.start()

            try:
                output_file = await requester.request(input_path, request_text)
                if not output_file:
                    msg = "Failed to process request"
                    logger.error(msg)
                    await progress.stop("Error: Analysis failed")
                    return msg

                await progress.stop("Analysis complete")
                logger.info("Request analysis complete: %s", output_file)
                return str(output_file)

            except Exception as e:
                logger.error("Error during request analysis: %s", str(e))
                await progress.stop("Error: Analysis failed")
                return f"Error during request analysis: {str(e)}"

        except Exception as e:
            logger.error("Error during request analysis: %s", str(e))
            return f"Error during request analysis: {str(e)}"

    def format_result(self, result: str) -> dict[str, Any]:
        """Format tool result for terminal output.

        Args:
            result: Raw tool result string

        Returns:
            Formatted result dictionary
        """
        return {"result": result}
