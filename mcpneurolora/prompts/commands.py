"""Command prompts for MCP server."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CommandHelpInput(BaseModel):
    """Input for command help prompt."""

    command: str = Field(..., description="Name of the command to get help for")


class CommandHelpOutput(BaseModel):
    """Output for command help prompt."""

    title: str = Field(..., description="Command name with emoji")
    description: str = Field(..., description="Command description")
    usage: str = Field(..., description="Command usage syntax")
    examples: List[str] = Field(..., description="Command usage examples")


class CommandMenuItem(BaseModel):
    """Menu item for command menu prompt."""

    command: str = Field(..., description="Command name")
    title: str = Field(..., description="Command name with emoji")
    description: str = Field(..., description="Short description")
    preview: str = Field(..., description="Example usage")


class CommandSuggestionInput(BaseModel):
    """Input for command suggestion prompt."""

    command: str = Field(..., description="The command that was executed")
    success: bool = Field(..., description="Whether the command succeeded")
    error: Optional[str] = Field(None, description="Error message if command failed")


class CommandSuggestionOutput(BaseModel):
    """Output for command suggestion prompt."""

    message: List[str] = Field(..., description="Status messages")
    suggestions: List[str] = Field(..., description="Suggested next actions")


class CommandRoutingInput(BaseModel):
    """Input for command routing prompt."""

    text: str = Field(..., description="Natural language command to route")


class CommandRoutingOutput(BaseModel):
    """Output for command routing prompt."""

    command: str = Field(..., description="Selected command name")
    confidence: float = Field(
        ...,
        description="Confidence score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    reason: str = Field(..., description="Explanation for selection")
