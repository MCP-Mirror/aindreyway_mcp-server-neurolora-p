"""AI-based code request handler."""

from pathlib import Path
from typing import List, Optional, Union

from ..file_naming import FileType
from .base_analyzer import BaseAnalyzer


class Requester(BaseAnalyzer):
    """Main class for handling code requests using AI analysis."""

    async def request(
        self,
        input_paths: Union[str, List[str]],
        request_text: str,
    ) -> Optional[Path]:
        """Process a code request using AI analysis.

        Args:
            input_paths: Path(s) to analyze
            request_text: User's request text

        Returns:
            Optional[Path]: Path to generated analysis file or None if failed
        """
        extra_content = f"FEATURE REQUEST:\n{request_text}\n\nCODE:"
        return await self.analyze_code(
            input_paths=input_paths,
            title="Code Request Analysis",
            prompt_name="request",
            output_type=FileType.REQUEST_RESULT,
            extra_content=extra_content,
        )
