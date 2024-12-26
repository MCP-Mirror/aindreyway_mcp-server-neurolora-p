#!/usr/bin/env python3
"""Pre-commit script for running code quality checks."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Tuple


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


class Check(NamedTuple):
    """Represents a pre-commit check with its command and description."""

    command: List[str]
    description: str


def run_command(command: List[str], description: str) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n{description}...")
    try:
        # Run with direct output to terminal
        result = subprocess.run(
            command,
            check=False,  # Don't raise exception on non-zero exit
            env={
                **os.environ,
                "FORCE_COLOR": "1",  # Force colored output
                "PY_COLORS": "1",
                "MYPY_FORCE_COLOR": "1",
                "PYTEST_FORCE_COLOR": "1",
            },
        )
        return result.returncode == 0, ""
    except Exception as e:
        return False, f"Failed to run command: {e}"


def main() -> int:
    """Run all pre-commit checks."""
    python_path = get_python_path()
    checks: List[Check] = [
        Check(
            command=[
                python_path,
                "-m",
                "pytest",
                "-v",
                "--cov=mcp_server_neurolorap",
                "--cov-report=term-missing",
            ],
            description="Running tests with coverage",
        ),
        Check(
            command=[python_path, "-m", "black", "."],
            description="Formatting code with black",
        ),
        Check(
            command=[python_path, "-m", "isort", "."],
            description="Sorting imports with isort",
        ),
        Check(
            command=[python_path, "-m", "flake8", "."],
            description="Checking code style with flake8",
        ),
        Check(
            command=[
                python_path,
                "-m",
                "mypy",
                "src/mcp_server_neurolorap",
                "tests",
            ],
            description="Checking types with mypy",
        ),
    ]

    failed_checks: List[Tuple[str, str]] = []
    any_formatted: bool = False

    for check in checks:
        success, error = run_command(check.command, check.description)
        if not success:
            if check.description in [
                "Formatting code with black",
                "Sorting imports with isort",
            ]:
                # Tools like black return 1 if they modified files
                any_formatted = True
            else:
                failed_checks.append((check.description, error))

    if any_formatted:
        print("\n⚠️  Some files were reformatted.")
        print("Please review and stage the changes.")
        return 1

    if failed_checks:
        print("\n❌ Some checks failed:")
        for description, error in failed_checks:
            if error:  # Only print if there's an error message
                print(f"\n{description}:")
                print(error)
        return 1

    print("\n✨ All checks passed successfully! ✨")
    print("You can now commit and push your changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
