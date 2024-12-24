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
├── tests/                     # Test directory (to be implemented)
│   ├── unit/                 # Unit tests
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

## Task List

### Core Functionality

- [x] Set up project structure
- [x] Implement MCP server using FastMCP
- [x] Create code collector class
- [x] Add language detection
- [x] Implement ignore patterns
- [x] Generate markdown output
- [x] Add table of contents
- [x] Support multiple input paths

### Documentation

- [x] Create README.md
- [x] Add PROJECT_SUMMARY.md
- [x] Document code with docstrings
- [x] Add type hints

### Development

- [x] Configure development tools
  - [x] black for formatting
  - [x] isort for import sorting
  - [x] flake8 for linting
  - [x] mypy for type checking with strict mode
- [x] Set up virtual environment (.venv)
- [x] Add package dependencies
  - [x] mcp (Python SDK for MCP)
  - [x] markdown for document generation
  - [x] pygments for syntax highlighting
  - [x] typing-extensions for enhanced type hints

### Testing

- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Add test documentation

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

- [x] Add developer mode with JSON-RPC terminal
- [x] Implement proper file storage structure
- [x] Add support for multiple projects
- [x] Implement robust file system synchronization
- [x] Add comprehensive error handling and logging
- [ ] Add support for binary files
- [ ] Implement file size limits configuration
- [ ] Add output format customization
- [ ] Support for additional markup formats
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
