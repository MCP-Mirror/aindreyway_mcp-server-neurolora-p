#!/usr/bin/env python3
"""Pre-commit script for running code quality checks."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List


def get_python_path() -> str:
    """Get the path to the Python interpreter from virtual environment."""
    venv_path = Path(".venv/bin/python")
    if venv_path.exists():
        return str(venv_path)
    venv_path = Path("venv/bin/python")  # alternative venv name
    if venv_path.exists():
        return str(venv_path)
    venv_path = Path(".venv/Scripts/python.exe")  # Windows path
    if venv_path.exists():
        return str(venv_path)
    venv_path = Path("venv/Scripts/python.exe")  # Windows alternative
    if venv_path.exists():
        return str(venv_path)
    return "python"  # fallback to system python if venv not found


def run_command(command: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(
            command,
            check=False,
            env={
                **os.environ,
                "FORCE_COLOR": "1",
                "PY_COLORS": "1",
                "MYPY_FORCE_COLOR": "1",
                "PYTEST_FORCE_COLOR": "1",
            },
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run command: {e}")
        return False


def main() -> int:
    """Run all pre-commit checks."""
    python_path = get_python_path()

    # Define checks as tuples of (description, command)
    checks = [
        (
            "Running tests with coverage",
            [
                python_path,
                "-m",
                "pytest",
                "-v",
                "--cov=mcp_server_neurolora",
                "--cov-report=term-missing",
            ],
        ),
        ("Formatting code with black", [python_path, "-m", "black", "."]),
        ("Sorting imports with isort", [python_path, "-m", "isort", "."]),
        (
            "Checking code style with flake8",
            [python_path, "-m", "flake8", "."],
        ),
        (
            "Checking types with mypy",
            [python_path, "-m", "mypy", "src/mcp_server_neurolora", "tests"],
        ),
    ]

    formatting_tools = {
        "Formatting code with black",
        "Sorting imports with isort",
    }
    failed_checks: List[str] = []

    for description, command in checks:
        if not run_command(command, description):
            if description in formatting_tools:
                print("\n⚠️  Files were reformatted.")
                print("Please review and stage changes.")
                return 1
            failed_checks.append(description)

    if failed_checks:
        print("\n❌ Failed checks:")
        for check in failed_checks:
            print(f"- {check}")
        return 1

    print("\n✨ All checks passed successfully! ✨")
    print("You can now commit and push your changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
