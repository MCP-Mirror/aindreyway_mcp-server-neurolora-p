"""Progress tracking utilities."""

import asyncio
import logging
import sys
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track progress of long-running operations.

    This class provides a way to track and report progress for operations
    like code analysis and API requests. It supports:
    - Adaptive timing based on content length
    - Real-time progress updates with spinner animation
    - Custom progress messages
    - Start/stop timing
    - ETA calculation
    """

    def __init__(
        self,
        total_steps: int = 100,
        prefix: str = "",
        content_length: Optional[int] = None,
        use_spinner: bool = True,
    ) -> None:
        """Initialize progress tracker.

        Args:
            total_steps: Total number of steps (default: 100)
            prefix: Prefix for progress messages
            content_length: Optional content length for adaptive timing
            use_spinner: Whether to use spinner animation (default: True)
        """
        self.total_steps = total_steps
        self.prefix = prefix
        self.content_length = content_length
        self.use_spinner = use_spinner
        self.current_step = 0
        self.start_time: Optional[float] = None
        self._last_update = 0.0
        self._update_interval = 0.1  # seconds
        self.is_running = False

        # Spinner animation
        self.spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0

        # Adaptive timing based on content length
        if content_length:
            # Estimate processing time based on content length
            # Rough estimate: 1 second per 4000 chars with minimum of 10s
            self.estimated_time = max(10, content_length / 4000)
        else:
            self.estimated_time = 60  # Default 1 minute

    async def start(self) -> None:
        """Start progress tracking."""
        self.start_time = time.time()
        self.current_step = 0
        self.is_running = True
        if self.use_spinner:
            asyncio.create_task(self._update_loop())
        await self._log_progress("Started")

    async def stop(self, message: str = "Complete") -> None:
        """Stop progress tracking.

        Args:
            message: Optional completion message
        """
        self.is_running = False
        if self.start_time is not None:
            duration = time.time() - self.start_time
            if self.use_spinner:
                sys.stdout.write("\r" + " " * 80 + "\r")  # Clear line
                sys.stdout.write(
                    f"{self.prefix} {message} ({duration:.1f}s)\n"
                )
                sys.stdout.flush()
            else:
                await self._log_progress(
                    f"{message} in {duration:.1f}s",
                    force=True,
                )
        self.start_time = None

    async def update(self, step: int, message: str = "") -> None:
        """Update progress to a specific step.

        Args:
            step: Current step number (0-100)
            message: Optional progress message
        """
        if not self.is_running:
            return

        now = time.time()
        self.current_step = min(step, self.total_steps)

        # Only update if enough time has passed
        if (now - self._last_update) >= self._update_interval:
            if self.use_spinner:
                self._update_display(message)
            else:
                await self._log_progress(self._format_progress(message))
            self._last_update = now

    async def increment(self) -> None:
        """Increment progress by one step."""
        if not self.is_running:
            return
        await self.update(self.current_step + 1)

    def _format_progress(self, message: str = "") -> str:
        """Format progress message with all information.

        Args:
            message: Optional additional message

        Returns:
            Formatted progress string
        """
        now = time.time()
        progress = min(self.current_step / self.total_steps, 1.0)
        percent = int(progress * 100)

        # Calculate ETA if we have start time
        eta_str = ""
        if self.start_time is not None:
            elapsed = now - self.start_time
            if self.current_step > 0:
                total_estimated = (
                    elapsed / self.current_step
                ) * self.total_steps
                remaining = max(0, total_estimated - elapsed)
                eta_str = f"ETA: {remaining:.1f}s"

        # Add content length info
        content_info = ""
        if self.content_length:
            content_kb = self.content_length / 1024
            content_info = f"[{content_kb:.1f}KB] "

        # Update progress during API request
        if "Analysis" in self.prefix:
            elapsed = now - (self.start_time or now)
            # Calculate progress based on elapsed time and estimated time
            progress = min(elapsed / self.estimated_time, 0.95)  # Cap at 95%
            self.current_step = int(progress * self.total_steps)

            # Accelerate progress as we get closer to estimated time
            if elapsed > self.estimated_time * 0.8:
                # Increase progress more rapidly in final 20% of estimated time
                extra_progress = (elapsed - self.estimated_time * 0.8) / (
                    self.estimated_time * 0.2
                )
                self.current_step = min(
                    int((0.95 + extra_progress * 0.05) * self.total_steps),
                    self.total_steps,
                )

            progress = self.current_step / self.total_steps
            percent = int(progress * 100)

        # Format progress bar
        bar_width = 20
        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Format final message
        duration = now - (self.start_time or now)
        if duration >= 1:
            return (
                f"{self.prefix} {content_info}{bar} {percent}% "
                f"{message} ({duration:.1f}s) {eta_str}"
            ).strip()
        else:
            return (
                f"{self.prefix} {content_info}{bar} {percent}% {message}"
            ).strip()

    async def _update_loop(self) -> None:
        """Continuously update progress display."""
        while self.is_running:
            self._update_display()
            await asyncio.sleep(0.1)  # Update every 100ms

    def _update_display(self, message: str = "") -> None:
        """Update progress display with spinner animation.

        Args:
            message: Optional progress message
        """
        if not self.is_running:
            return

        # Update spinner
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner)
        spinner = self.spinner[self.spinner_idx]

        # Format progress message
        progress_msg = self._format_progress(message)

        # Write to stdout with spinner
        sys.stdout.write(f"\r{spinner} {progress_msg}")
        sys.stdout.flush()

    async def _log_progress(
        self, message: str = "", force: bool = False
    ) -> None:
        """Log progress message.

        Args:
            message: Progress message to log
            force: Force update even if interval hasn't elapsed
        """
        if force or (time.time() - self._last_update) >= self._update_interval:
            logger.info(message)
            self._last_update = time.time()
            # Small delay to allow other tasks to run
            await asyncio.sleep(0)
