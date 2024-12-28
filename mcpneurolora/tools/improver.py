"""AI-based code improvement suggestions."""

from pathlib import Path
from typing import Optional, Union, List

from ..file_naming import FileType
from .base_analyzer import BaseAnalyzer


class Improver(BaseAnalyzer):
    """Main class for improving code using AI analysis."""

    async def improve(
        self,
        input_paths: Union[str, List[str]],
    ) -> Optional[Path]:
        """Analyze code and suggest improvements.

        Args:
            input_paths: Path(s) to analyze

        Returns:
            Optional[Path]: Path to generated analysis file or None if failed
        """
        return await self.analyze_code(
            input_paths=input_paths,
            title="Code Improvement Suggestions",
            prompt_name="improve",
            output_type=FileType.IMPROVE_RESULT,
            extra_content="Code to improve:",
        )
