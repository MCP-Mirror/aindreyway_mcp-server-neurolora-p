# MCP Server Neurolorap

This MCP server follows best practices for Model Context Protocol server development:

- Uses standardized directory structure
- Maintains single virtual environment (.venv)
- Follows modular architecture
- Implements clear separation of concerns

## Overview

MCP server providing tools for code analysis and documentation:

1. Code Collection Tool:

   - Collects code from files/directories into a single markdown document
   - Syntax highlighting based on file extensions
   - Table of contents for easy navigation
   - Support for multiple programming languages
   - Customizable file ignore patterns

2. Project Structure Reporter Tool:
   - Analyzes project structure and metrics
   - Generates detailed reports in markdown format
   - File size and complexity analysis
   - Recommendations for code organization
   - Tree-based visualization of project structure

## Architecture

The project follows MCP server best practices with a clean, modular architecture:

```
mcp-server-neurolorap/
├── .venv/                     # Single virtual environment for development
├── src/
│   └── mcp_server_neurolorap/
│       ├── __init__.py          # Package initialization
│       ├── server.py            # MCP server implementation
│       ├── collector.py         # Code collection logic
│       ├── project_structure_reporter.py  # Structure analysis
│       ├── terminal.py          # Developer mode JSON-RPC terminal
│       ├── storage.py           # Storage management
│       ├── types.py            # Type definitions
│       ├── default.neuroloraignore  # Default ignore patterns
│       └── py.typed             # Type hints marker
├── tests/                     # Test directory
│   ├── unit/                 # Unit tests
│   │   ├── test_collector.py # Tests for collector.py
│   │   ├── test_storage.py  # Tests for storage.py
│   │   ├── test_server.py   # Tests for server.py
│   │   └── test_terminal.py # Tests for terminal.py
│   └── integration/         # Integration tests
├── pyproject.toml            # Project configuration
├── README.md                # User documentation
├── .neuroloraignore        # Project ignore patterns
├── pre-commit.py           # Pre-commit quality checks script with colored output
└── LICENSE                  # MIT License
```

### Storage Structure

```
~/.mcp-docs/                # Global storage directory
└── <project-name>/         # Project-specific storage
    ├── FULL_CODE_*.md      # Generated code collections
    ├── PROJECT_STRUCTURE_*.md  # Structure reports
    └── PROMPT_ANALYZE_*.md # Analysis prompts

<project-root>/
└── .neurolora -> ~/.mcp-docs/<project-name>/  # Symlink to storage
```

### Development Environment

- Single `.venv` virtual environment for dependency isolation
- `pyproject.toml` for modern Python packaging
- Type hints throughout codebase
- Standardized ignore patterns

### Components

1. **Server (server.py)**

   - Implements MCP protocol using FastMCP with modern Python features
   - Exposes code collection and structure analysis tools
   - Uses dependency injection for required packages
   - Handles request/response lifecycle with proper error handling
   - Includes developer mode with JSON-RPC terminal interface

2. **Terminal (terminal.py)**

   - Implements JSON-RPC 2.0 protocol for developer mode
   - Provides interactive command-line interface
   - Supports extensible command system
   - Includes built-in help and documentation

3. **Collector (collector.py)**

   - Core code collection functionality
   - File traversal and filtering
   - Markdown generation
   - Language detection

4. **Project Structure Reporter (project_structure_reporter.py)**

   - Project structure analysis
   - File metrics collection:
     - Size analysis
     - Line counting
     - Token estimation
   - Complexity assessment
   - Report generation in markdown format
   - Tree-based visualization
   - Recommendations for code organization

5. **Storage (storage.py)**

   - Manages file storage and organization
   - Creates and maintains .neurolora symlink in project root
   - Handles file paths and project structure
   - Ensures robust file system synchronization:
     - Uses forced file synchronization (os.fsync)
     - Implements global file system sync (os.sync)
     - Updates modification times for directory chain
     - Includes small delays for filesystem stability
   - Manages .neuroloraignore patterns
   - Provides comprehensive error handling and logging

6. **Configuration**
   - .neuroloraignore support
   - Default ignore patterns
   - Language mappings

## Testing

The project uses pytest for testing and includes comprehensive test coverage across multiple categories:

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── test_collector.py # Tests for collector.py
│   ├── test_storage.py  # Tests for storage.py
│   ├── test_server.py   # Tests for server.py
│   └── test_terminal.py # Tests for terminal.py
└── integration/         # Integration tests
```

### Test Categories

1. **Unit Tests**

   - Test individual components in isolation
   - Mock external dependencies
   - Focus on edge cases and error handling
   - Verify type annotations and interfaces
   - Test each public method and class

2. **Integration Tests**

   - Test component interactions
   - Verify file system operations
   - Test JSON-RPC protocol compliance
   - Validate MCP tool functionality
   - Test error propagation between components

3. **Performance Tests**

   - Test system performance under load
   - Measure file processing speed
   - Monitor memory usage patterns
   - Test concurrent operations
   - Verify resource cleanup

4. **Security Tests**
   - Test input validation
   - Verify file permissions
   - Test path traversal prevention
   - Check symlink handling
   - Validate error messages

### Test Infrastructure

1. **Tools and Libraries**

   - pytest for test framework
   - pytest-asyncio for async tests
   - pytest-cov for coverage reporting
   - pytest-xdist for parallel execution
   - pytest-timeout for test timeouts
   - pytest-randomly for random ordering

2. **CI/CD Integration**

   - GitHub Actions workflow
   - Automated test execution
   - Coverage reporting
   - Code quality checks
   - Security scanning

3. **Coverage Requirements**

   - Minimum 80% code coverage (current: 83.65%)
   - All public interfaces tested
   - Error paths verified
   - Edge cases covered
   - Documentation examples tested

4. **Current Coverage Status**

   - **init**.py: 100% (fully covered)
   - **main**.py: 96% (missing lines 109, 169)
   - collector.py: 84% (meets minimum requirement)
   - project_structure_reporter.py: 79% (needs improvement)
   - server.py: 66% (needs improvement in lines 45-72, 81-110, 150->161, 158->161)
   - storage.py: 80% (meets minimum requirement)
   - terminal.py: 71% (needs improvement)
   - types.py: 85% (meets minimum requirement)

   Total coverage: 80.04% (meets minimum requirement of 80%)

### Pre-commit Checks

Before committing code to GitHub, run the pre-commit script to ensure all quality standards are met:

```bash
# Run all checks using the pre-commit script
python pre-commit.py
```

The script will automatically run all necessary checks in sequence with beautiful colored output:

This command will:

1. Run all tests with coverage reporting
2. Format code with black
3. Sort imports with isort
4. Check code style with flake8
5. Verify type hints with mypy

The command will fail if any of these checks fail:

- Tests must pass with minimum 80% coverage
- Code must be properly formatted (black)
- Imports must be properly sorted (isort)
- No style violations (flake8)
- No type errors (mypy)

Only commit and push code when all checks pass successfully. This ensures our CI/CD pipelines will always succeed.

### Running Individual Checks

For development, you can run individual checks:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server_neurolorap

# Run specific categories
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m "not slow"    # Skip slow tests

# Run in parallel
pytest -n auto

# Show test timing
pytest --durations=10

# Generate coverage report
pytest --cov-report=html

# Format code
black .

# Sort imports
isort .

# Check style
flake8 .

# Check types
mypy src/mcp_server_neurolorap tests
```

## Developer Mode

The server includes a developer mode with JSON-RPC terminal interface that allows direct interaction with the server's functionality. To use developer mode:

```bash
# Start the server in developer mode
python -m mcp_server_neurolorap --dev

# Available commands in the terminal:
> help                    # Show available commands
> list_tools             # List available MCP tools
> collect <path>         # Collect code from specified path
> report [path]          # Generate project structure report
> exit                   # Exit developer mode
```

Example session:

```
> help
Available commands:
- help: Show this help message
- list_tools: List available MCP tools
- collect <path>: Collect code from specified path
- report [path]: Generate project structure report
- exit: Exit the terminal

> list_tools
["code_collector", "project_structure_reporter"]

> collect src
Code collection complete!
Output file: code_collection.md

> report
Project structure report generated: PROJECT_STRUCTURE_REPORT.md

> exit
Goodbye!
```

## Future Improvements

### Features

1. Binary File Support

   - Support for reading and processing binary files
   - Safe binary file detection
   - Binary file size limits
   - Support for common binary formats (PDF, images, etc.)

2. File Size Management

   - Configurable file size limits
   - Large file handling strategies
   - File chunking for large files
   - File size warnings and notifications

3. Output Customization

   - Multiple output formats (MD, HTML, PDF)
   - Custom templates for output
   - Syntax highlighting themes
   - Table of contents customization
   - Custom metadata fields

4. Markup Support
   - Support for AsciiDoc
   - Support for reStructuredText
   - Custom markup formats
   - Markup conversion utilities

### Performance

1. Progress Reporting

   - Real-time progress indicators
   - ETA calculations
   - Detailed progress statistics
   - Progress callbacks

2. Caching System

   - Smart file caching
   - Cache invalidation strategies
   - Incremental updates
   - Cache size management

3. Parallel Processing
   - Multi-threaded file processing
   - Worker pool management
   - Concurrent file access handling
   - Distributed processing

## Usage Examples

### Code Collection

```python
# Collect code from entire project
result = use_mcp_tool(
    "code_collector",
    {
        "input": ".",
        "title": "My Project"
    }
)

# Collect code from specific directory
result = use_mcp_tool(
    "code_collector",
    {
        "input": "./src",
        "title": "Source Code"
    }
)

# Collect code from multiple paths
result = use_mcp_tool(
    "code_collector",
    {
        "input": ["./src", "./tests"],
        "title": "Project Files"
    }
)
```

### Project Structure Analysis

```python
# Generate project structure report
result = use_mcp_tool(
    "project_structure_reporter",
    {
        "output_filename": "PROJECT_STRUCTURE_REPORT.md"
    }
)

# Analyze specific directory with custom ignore patterns
result = use_mcp_tool(
    "project_structure_reporter",
    {
        "output_filename": "src_structure.md",
        "ignore_patterns": ["*.pyc", "__pycache__"]
    }
)
```
