#!/usr/bin/env python3
"""Run all tests with coverage reporting."""

import subprocess
import sys
from typing import List, Optional


def run_tests(args: Optional[List[str]] = None) -> int:
    """Run pytest with coverage reporting.

    Args:
        args: Additional pytest arguments

    Returns:
        Exit code from pytest
    """
    test_args = args if args is not None else []

    # Base pytest command with coverage
    cmd = [
        "pytest",
        "--cov=mcpneurolora",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-fail-under=80",
    ]

    # Add custom arguments
    cmd.extend(test_args)

    # Run tests
    try:
        return subprocess.run(cmd, check=True).returncode
    except subprocess.CalledProcessError as e:
        return e.returncode


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Get arguments after script name
    args = sys.argv[1:]

    # Default to running all tests if no arguments provided
    if not args:
        print("Running all tests...")
        return run_tests()

    # Run specific test categories based on arguments
    if "--unit" in args:
        print("Running unit tests...")
        args.remove("--unit")
        return run_tests(["-m", "unit"] + args)

    if "--integration" in args:
        print("Running integration tests...")
        args.remove("--integration")
        return run_tests(["-m", "integration"] + args)

    if "--slow" in args:
        print("Running slow tests...")
        args.remove("--slow")
        return run_tests(["-m", "slow"] + args)

    # Pass through any other arguments to pytest
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
