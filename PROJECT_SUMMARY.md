# MCP Server Neurolorap

This MCP server follows best practices for Model Context Protocol server development:

- Uses standardized directory structure
- Maintains single virtual environment (.venv)
- Follows modular architecture
- Implements clear separation of concerns

## Overview

MCP server for collecting code from files and directories into a single markdown document. This server provides a tool for documenting code bases by generating comprehensive markdown files that include:

- Code from specified files/directories
- Syntax highlighting based on file extensions
- Table of contents for easy navigation
- Support for multiple programming languages
- Customizable file ignore patterns

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
└── LICENSE                  # MIT License
```

### Storage Structure

```
~/.mcp-docs/                # Global storage directory
└── <project-name>/         # Project-specific storage
    ├── FULL_CODE_*.md      # Generated code collections
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
   - Exposes code collection tool with proper type hints
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

4. **Storage (storage.py)**

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

5. **Configuration**
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

   - Minimum 80% code coverage (current: 82.63%)
   - All public interfaces tested
   - Error paths verified
   - Edge cases covered
   - Documentation examples tested

4. **Current Coverage Status**

   - **init**.py: 100% (fully covered)
   - **main**.py: 96% (missing lines 109, 169)
   - collector.py: 83% (meets minimum requirement)
   - server.py: 68% (needs improvement in lines 43-84 and condition 116->119)
   - storage.py: 80% (meets minimum requirement)
   - terminal.py: 94% (high coverage)
   - types.py: 83% (meets minimum requirement)

   Total coverage: 83.65% (exceeds minimum requirement of 80%)

### Running Tests

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
```

## Task List

### Completed Tasks

#### Testing Infrastructure

- [x] Set up test infrastructure
  - [x] Configure pytest
  - [x] Add coverage reporting
  - [x] Set up CI/CD pipeline
  - [x] Add test categories
- [x] Add unit tests
  - [x] Test collector functionality (83% coverage)
  - [x] Test storage operations (80% coverage)
  - [x] Test server implementation (68% coverage)
  - [x] Test terminal interface (94% coverage)
- [x] Achieve minimum code coverage requirement (83.65% > 80%)

#### Developer Mode

- [x] Add developer mode with JSON-RPC terminal
- [x] Implement proper file storage structure
- [x] Add support for multiple projects
- [x] Implement robust file system synchronization
- [x] Add comprehensive error handling and logging

### Pending Tasks

#### Testing

- [ ] Add integration tests
  - [ ] Test component interactions
  - [ ] Test file system operations
  - [ ] Test error propagation
- [ ] Add performance tests
  - [ ] Test system under load
  - [ ] Measure resource usage
  - [ ] Test concurrent operations
- [ ] Add security tests
  - [ ] Test input validation
  - [ ] Test file permissions
  - [ ] Test path traversal prevention

### Developer Mode

The server includes a developer mode with JSON-RPC terminal interface that allows direct interaction with the server's functionality. To use developer mode:

```bash
# Start the server in developer mode
python -m mcp_server_neurolorap --dev

# Available commands in the terminal:
> help                    # Show available commands
> list_tools             # List available MCP tools
> collect <path>         # Collect code from specified path
> exit                   # Exit developer mode
```

Example session:

```
> help
Available commands:
- help: Show this help message
- list_tools: List available MCP tools
- collect <path>: Collect code from specified path
- exit: Exit the terminal

> list_tools
["code-collector"]

> collect src
Code collection complete!
Output file: code_collection.md

> exit
Goodbye!
```

### Future Improvements

#### Features

- [ ] Add support for binary files
- [ ] Implement file size limits configuration
- [ ] Add output format customization
- [ ] Support for additional markup formats

#### Performance

- [ ] Add progress reporting
- [ ] Implement caching for large codebases
- [ ] Add parallel processing for better performance

## Usage Examples

```python
# Collect code from entire project
result = use_mcp_tool(
    "code-collector",
    {
        "input": ".",
        "title": "My Project"
    }
)

# Collect code from specific directory
result = use_mcp_tool(
    "code-collector",
    {
        "input": "./src",
        "title": "Source Code"
    }
)

# Collect code from multiple paths
result = use_mcp_tool(
    "code-collector",
    {
        "input": ["./src", "./tests"],
        "title": "Project Files"
    }
)
```
