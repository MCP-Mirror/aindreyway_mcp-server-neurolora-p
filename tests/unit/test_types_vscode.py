"""Tests for types/vscode.py module."""

from typing import Dict, List

from mcpneurolora.types.vscode import ServerConfig, ServerEnvConfig, VsCodeSettings


def test_server_env_config() -> None:
    """Test ServerEnvConfig type."""
    # Test with all optional fields
    config: ServerEnvConfig = {
        "AI_MODEL": "test-model",
        "OPENAI_API_KEY": "test-key",
        "GEMINI_API_KEY": "test-key",
        "AI_TIMEOUT_MS": "5000",
        "MAX_FILE_SIZE_MB": "10",
        "PREVIEW_SIZE_KB": "100",
        "PYTHONUNBUFFERED": "1",
    }
    assert isinstance(config, dict)
    assert all(isinstance(v, str) for v in config.values())

    # Test with minimal fields
    minimal: ServerEnvConfig = {}
    assert isinstance(minimal, dict)


def test_server_config() -> None:
    """Test ServerConfig type."""
    # Test valid config
    config: ServerConfig = {
        "command": "test-command",
        "args": ["--arg1", "--arg2"],
        "disabled": False,
        "alwaysAllow": ["tool1", "tool2"],
        "env": {"KEY1": "value1", "KEY2": "value2"},
    }
    assert isinstance(config, dict)
    assert isinstance(config["command"], str)
    assert isinstance(config["args"], list)
    assert isinstance(config["disabled"], bool)
    assert isinstance(config["alwaysAllow"], list)
    assert isinstance(config["env"], dict)

    # Test required fields
    required_fields = {"command", "args", "disabled", "alwaysAllow", "env"}
    assert all(field in config for field in required_fields)


def test_vscode_settings() -> None:
    """Test VsCodeSettings type."""
    # Test valid settings
    settings: VsCodeSettings = {
        "mcpServers": {
            "server1": {
                "command": "test-command",
                "args": ["--arg1"],
                "disabled": False,
                "alwaysAllow": ["tool1"],
                "env": {"KEY1": "value1"},
            }
        }
    }
    assert isinstance(settings, dict)
    assert isinstance(settings["mcpServers"], dict)
    for server_config in settings["mcpServers"].values():
        assert isinstance(server_config, dict)
        assert isinstance(server_config["command"], str)
        assert isinstance(server_config["args"], list)
        assert isinstance(server_config["disabled"], bool)
        assert isinstance(server_config["alwaysAllow"], list)
        assert isinstance(server_config["env"], dict)


def test_type_compatibility() -> None:
    """Test type compatibility between related types."""
    # Test ServerConfig env compatibility
    env_config: Dict[str, str] = {
        "AI_MODEL": "test-model",
        "OPENAI_API_KEY": "test-key",
    }
    server_config: ServerConfig = {
        "command": "test",
        "args": [],
        "disabled": False,
        "alwaysAllow": [],
        "env": env_config,
    }
    assert isinstance(server_config, dict)

    # Test nested structure
    settings: VsCodeSettings = {
        "mcpServers": {
            "test-server": server_config,
        }
    }
    assert isinstance(settings, dict)
    assert isinstance(settings["mcpServers"], dict)


def test_type_annotations() -> None:
    """Test type annotations and hints."""
    # Test list type annotation
    args: List[str] = ["--arg1", "--arg2"]
    server_config: ServerConfig = {
        "command": "test",
        "args": args,
        "disabled": False,
        "alwaysAllow": [],
        "env": {},
    }
    assert isinstance(server_config["args"], list)
    assert all(isinstance(arg, str) for arg in server_config["args"])

    # Test dict type annotation
    env: Dict[str, str] = {"KEY1": "value1"}
    server_config = {
        "command": "test",
        "args": [],
        "disabled": False,
        "alwaysAllow": [],
        "env": env,
    }
    assert isinstance(server_config["env"], dict)
    assert all(
        isinstance(k, str) and isinstance(v, str)
        for k, v in server_config["env"].items()
    )
