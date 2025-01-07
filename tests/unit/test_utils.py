"""Tests for utility functions and classes."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest
from pydantic import BaseModel

from mcpneurolora.tools.definitions import COMMANDS
from mcpneurolora.utils import (
    ProgressTracker,
    count_tokens,
    file_lock,
    get_token_limit,
    sanitize_filename,
)
from mcpneurolora.utils.validation import (
    validate_arguments,
    validate_command,
    validate_command_model,
    validate_error_response,
    validate_model_type,
    validate_path,
)


def test_exports() -> None:
    """Test that all functions and classes are exported."""
    # Test that all functions are callable
    assert callable(file_lock)
    assert callable(validate_path)
    assert callable(sanitize_filename)
    assert callable(count_tokens)
    assert callable(get_token_limit)
    assert callable(validate_arguments)
    assert callable(validate_command)
    assert callable(validate_command_model)

    # Test that ProgressTracker is a class
    assert isinstance(ProgressTracker, type)


def test_validate_command() -> None:
    """Test command validation."""
    # Test valid MCP command
    for cmd_name, cmd_def in COMMANDS.items():
        if cmd_def["is_mcp_tool"]:
            validate_command(cmd_name)  # Should not raise

    # Test invalid command
    with pytest.raises(ValueError, match="Unknown tool"):
        validate_command("invalid_command")

    # Test non-MCP command
    for cmd_name, cmd_def in COMMANDS.items():
        if not cmd_def["is_mcp_tool"]:
            with pytest.raises(ValueError, match="Not an MCP tool"):
                validate_command(cmd_name)


def test_validate_command_model() -> None:
    """Test command model validation."""
    # Test command with model
    for cmd_name, cmd_def in COMMANDS.items():
        if cmd_def["model"]:
            model = validate_command_model(cmd_name)
            assert model == cmd_def["model"]

    # Test command without model
    for cmd_name, cmd_def in COMMANDS.items():
        if not cmd_def["model"]:
            with pytest.raises(ValueError, match="Tool has no input model"):
                validate_command_model(cmd_name)


def test_validate_path() -> None:
    """Test path validation."""
    # Test valid paths
    valid_paths: List[Union[str, Path]] = [
        "test.txt",
        "path/to/file.txt",
        Path("test.txt"),
        Path("path/to/file.txt"),
    ]
    for path in valid_paths:
        result = validate_path(path)
        assert isinstance(result, Path)

    # Test invalid paths
    invalid_paths: List[Any] = [None, 123, [], {}]
    for invalid_path in invalid_paths:
        with pytest.raises(ValueError, match="Invalid path type"):
            validate_path(invalid_path)

    # Test path with TypeError
    class PathWithTypeError:
        def __fspath__(self) -> None:
            raise TypeError("Test error")

    with pytest.raises(ValueError, match="Invalid path type"):
        validate_path(PathWithTypeError())  # type: ignore

    # Test path with other exceptions
    class PathWithError:
        def __fspath__(self) -> None:
            raise ValueError("Test error")

    with pytest.raises(ValueError, match="Invalid path"):
        validate_path(PathWithError())  # type: ignore


def test_validate_arguments() -> None:
    """Test argument validation."""

    class TestModel(BaseModel):
        """Test model for validation."""

        name: str
        count: int

    # Test valid arguments
    valid_args: Dict[str, Any] = {"name": "test", "count": 42}
    result = validate_arguments(TestModel, valid_args)
    assert isinstance(result, TestModel)
    assert result.name == "test"
    assert result.count == 42

    # Test validation error
    with pytest.raises(ValueError, match="Invalid arguments"):
        validate_arguments(TestModel, {"name": "test"})  # Missing required field

    # Test type error
    with pytest.raises(ValueError, match="Invalid arguments"):
        validate_arguments(TestModel, {"name": "test", "count": "not_a_number"})

    # Test unexpected error
    with pytest.raises(ValueError, match="Invalid arguments"):
        validate_arguments(object(), {})  # Pass non-model class


def test_validate_model_type() -> None:
    """Test model type validation."""

    class TestModel(BaseModel):
        """Test model for validation."""

        name: str

    # Test valid model type
    model = TestModel(name="test")
    result = validate_model_type(model, TestModel, "test_command")
    assert result == model

    # Test invalid model type
    with pytest.raises(ValueError, match="Invalid model type"):
        validate_model_type("not a model", TestModel, "test_command")


def test_validate_error_response() -> None:
    """Test error response validation."""
    # Test valid error response
    valid_error: Dict[str, str] = {"message": "Test error"}
    assert validate_error_response(valid_error) == "Test error"

    # Test invalid error responses
    invalid_errors: List[Optional[Dict[str, Any]]] = [
        None,  # Not a dict
        {},  # Empty dict
        {"message": ""},  # Empty message
        {"message": None},  # None message
        {"message": 123},  # Non-string message
        {"wrong_key": "message"},  # Missing message key
    ]
    for error in invalid_errors:
        assert validate_error_response(error) is None
