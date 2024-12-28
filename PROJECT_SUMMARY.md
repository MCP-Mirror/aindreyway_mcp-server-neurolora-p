# NeuroLoRA MCP Server - Developer Documentation

> **Note**: This document is intended for developers only. For user documentation, please see README.md.

This MCP server follows best practices for Model Context Protocol server development:

- Uses standardized directory structure
- Maintains single virtual environment (.venv)
- Follows modular architecture
- Implements clear separation of concerns

## Overview

MCP server providing tools for code analysis and documentation. The server has two levels of functionality:

### Base Tools (Always Available)

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

### AI-Powered Tools (Requires Configuration)

These tools are available only when AI model and API key are configured in Cline settings. Currently tested and supported only in Cline (not tested with Claude Desktop or other clients).

3. Find Improvements Tool:

   - Uses AI to analyze code and suggest improvements
   - Supports multiple AI providers:
     - OpenAI models:
       - o1 (200k tokens)
       - o1-preview (128k tokens)
       - o1-preview-2024-09-12 (128k tokens)
     - Gemini models:
       - gemini-2.0-flash-exp (1M tokens)
       - gemini-2.0-flash-thinking-exp-1219 (32k tokens)
     - Anthropic models:
       - claude-3-opus-20240229 (200k tokens)
       - claude-3-sonnet-20240229 (200k tokens)
       - claude-3-haiku-20240307 (200k tokens)
   - Model-based provider selection
   - Automatic token limit handling
   - Adaptive progress tracking with smart ETA estimation
   - Token count reporting for better resource management
   - 5-minute timeout for AI operations
   - Consistent file generation:
     - CODE\_\*.md - collected source code
     - IMPROVE*PROMPT*\*.md - analysis prompt
     - IMPROVE*RESULT*\*.md - analysis result

4. Code Request Tool:
   - Process natural language requests for code changes
   - Uses AI to generate detailed implementation plans
   - Same provider and model support as Improvements Tool
   - 5-minute timeout for AI operations
   - Consistent file generation:
     - CODE\_\*.md - collected source code
     - REQUEST*PROMPT*\*.md - request prompt
     - REQUEST*RESULT*\*.md - request result

### Required Configuration for AI Tools

To enable AI-powered tools, add the following to Cline settings:

```json
{
  "mcpServers": {
    "aindreyway-neurolora": {
      "command": "uvx",
      "args": ["mcp-server-neurolora"],
      "env": {
        "AI_MODEL": "o1-preview", // One of the supported models
        "OPENAI_API_KEY": "your-api-key", // Required for OpenAI models
        "GEMINI_API_KEY": "your-api-key", // Required for Gemini models
        "ANTHROPIC_API_KEY": "your-api-key" // Required for Anthropic models
      }
    }
  }
}
```

## Developer Mode

The server includes a developer mode with JSON-RPC terminal interface:

```bash
# IMPORTANT: Always use virtual environment (.venv) for all commands
.venv/bin/python -m mcpneurolora --dev

# DO NOT use system python directly:
# ❌ python -m mcpneurolora
# ✅ .venv/bin/python -m mcpneurolora

# Available commands:
> help                    # Show commands
> list_tools             # List tools
> collect <path>         # Collect code
> report [path]          # Generate report
> improve                # Analyze code
> exit                   # Exit

# Example session:
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

## Architecture

The project follows MCP server best practices with a clean, modular architecture:

```
aindreyway-mcp-server-neurolora/
├── .venv/                     # Single virtual environment for development
├── mcp_server_neurolora/    # Source code directory
│   ├── __init__.py           # Package initialization
│   ├── server.py             # MCP server implementation
│   ├── config.py             # Configuration management
│   ├── terminal.py           # Developer mode JSON-RPC terminal
│   ├── storage.py            # Storage management
│   ├── types.py              # Type definitions
│   ├── providers/            # AI provider implementations
│   │   ├── __init__.py      # Provider factory and configuration
│   │   ├── base_provider.py  # Base provider interface
│   │   ├── openai_provider.py # OpenAI implementation
│   │   ├── anthropic_provider.py # Anthropic implementation
│   │   └── gemini_provider.py # Gemini implementation
│   ├── tools/                # Tool implementations
│   │   ├── __init__.py      # Tool initialization
│   │   ├── collector.py      # Code collection tool
│   │   ├── improver.py       # Code improvement tool
│   │   ├── reporter.py       # Structure reporter tool
│   │   └── executor.py       # Tool execution management
│   ├── templates/            # Template files
│   │   ├── ignore.template   # Default ignore patterns
│   │   ├── todo.template.md  # TODO template
│   │   └── done.template.md  # DONE template
│   └── py.typed              # Type hints marker
├── tests/                    # Test directory
│   ├── unit/                # Unit tests
│   │   ├── test_collector.py # Tests for collector.py
│   │   ├── test_storage.py  # Tests for storage.py
│   │   ├── test_server.py   # Tests for server.py
│   │   └── test_terminal.py # Tests for terminal.py
│   └── integration/         # Integration tests
├── pyproject.toml           # Project configuration
├── README.md               # User documentation
├── .neuroloraignore       # Project ignore patterns
├── pre-commit.py          # Pre-commit quality checks script
└── LICENSE                # MIT License
```

### Storage Structure

```
~/.mcp-docs/                # Global storage directory
└── <project-name>/         # Project-specific storage
    └── PROJECT_STRUCTURE_*.md  # Structure reports

<project-root>/
└── .neurolora -> ~/.mcp-docs/<project-name>/  # Symlink to storage
```

### Configuration System

The server uses a robust configuration management system:

1. **Environment Management**

   - Smart environment variable handling
   - Preserves existing variables during reload
   - Only sets new variables if not present
   - Validates required variables
   - Secure API key management
   - Detailed logging of configuration changes

2. **Required Configuration**

   - AI_MODEL: Model name (e.g. "o1", "gemini-2.0-flash-exp")
   - Provider-specific API keys:
     - OPENAI_API_KEY for OpenAI models
     - GEMINI_API_KEY for Gemini models
     - ANTHROPIC_API_KEY for Anthropic models
   - Project root path
   - Storage directory location

3. **Logging System**

   - Configurable logging levels for all components
   - Global logging configuration for MCP modules
   - Component-specific log filtering
   - Detailed operation logging
   - Progress tracking in terminal mode
   - Smart log filtering for cleaner output

4. **File Configuration**
   - .neuroloraignore support
   - Default ignore patterns
   - Language mappings
   - Project-specific settings

### AI Providers

The server implements a flexible AI provider system:

1. **Provider Architecture**

   - Base provider interface
   - Type-safe provider implementations
   - Common message format
   - Standardized error handling
   - Token limit validation
   - Response format validation
   - Proper resource cleanup
   - Efficient token counting

2. **Supported Models**

   - OpenAI models:
     - o1: 200,000 tokens
     - o1-preview-2024-09-12: 128,000 tokens
   - Gemini models:
     - gemini-2.0-flash-exp: 1,048,576 tokens
     - gemini-2.0-flash-thinking-exp-1219: 32,767 tokens
   - Anthropic models:
     - claude-3-opus-20240229: 200,000 tokens
     - claude-3-sonnet-20240229: 200,000 tokens
     - claude-3-haiku-20240307: 200,000 tokens

3. **Progress Tracking**

   - Adaptive progress tracking
   - Smart ETA estimation based on content size
   - Real-time progress updates
   - Accelerated progress in final stages
   - Detailed timing information
   - Token usage reporting

4. **Provider Selection**
   - Automatic provider selection based on model
   - Token limit validation
   - Model capability checking
   - Fallback handling
   - Error recovery

### Prompts System

The server implements a comprehensive prompts system using MCP prompts:

1. **Prompt Structure**

   - Markdown templates (.prompt.md files)
   - Pydantic models for type safety
   - Decorator-based registration (@mcp.prompt())
   - URI-based access (prompts://)

2. **Available Prompts**

   - Command Help (prompts://commands/{command}/help):

     - Get detailed help for specific commands
     - Usage examples and parameters
     - Command-specific tips

   - Command Menu (prompts://commands/menu):

     - List all available commands
     - Command descriptions and previews
     - Quick access to common actions

   - Command Suggestions (prompts://commands/{command}/suggest):

     - Context-aware next action suggestions
     - Error recovery recommendations
     - Success path guidance

   - Command Routing (prompts://commands):
     - Natural language command routing
     - Pattern-based command matching
     - Confidence scoring (0.0-1.0)
     - Multilingual support:
       - English commands (e.g., "collect code", "analyze code")
       - Russian commands (e.g., "собери код", "собрать код")
     - Command routing through FastMCP:
       - Automatic routing in call_tool_wrapper
       - High confidence threshold (>= 0.7)
       - Detailed logging of routing decisions

3. **Implementation**

   - Prompts directory structure:

     ```
     prompts/
     ├── __init__.py          # Prompt registration
     ├── commands.py          # Pydantic models
     └── commands.prompt.md   # Prompt templates
     ```

   - Type-safe prompt handling:

     - Input/output validation
     - Schema enforcement
     - Error handling

   - Standardized prompt format:
     - Clear sections (Input, Example, Response)
     - JSON schema definitions
     - Markdown formatting

4. **Usage**

   - Through MCP resources:

     ```python
     content = await client.read_resource(
         "local-aindreyway-neurolora",
         "prompts://commands/improve/help"
     )
     ```

   - Command routing:
     - Natural language -> Command mapping
     - Pattern matching using prompt templates
     - Confidence-based selection

### Components

1. **Server (server.py)**

   - Implements MCP protocol using FastMCP
   - Exposes code collection and analysis tools
   - Uses dependency injection
   - Handles request/response lifecycle
   - Includes developer mode with JSON-RPC terminal
   - Unified logging through ToolExecutor

2. **Tool Executor (tools/executor.py)**

   - Central component for tool execution
   - Unified interface for MCP and terminal
   - Consistent logging and error reporting
   - Tool lifecycle management
   - Resource cleanup

3. **Terminal (terminal.py)**

   - JSON-RPC 2.0 protocol implementation
   - Interactive command-line interface
   - Extensible command system
   - Built-in help and documentation
   - Command history
   - Tab completion

4. **Tools**

   - Collector (tools/collector.py):
     - Code collection functionality
     - File traversal and filtering
     - Markdown generation
     - Language detection
   - Improver (tools/improver.py):
     - Code analysis and improvement
     - AI provider integration
     - Progress tracking
     - Result formatting
   - Reporter (tools/reporter.py):
     - Project structure analysis
     - Metrics collection
     - Report generation
     - Recommendations

5. **Storage (storage.py)**
   - File storage management
   - .neurolora symlink handling
   - File path management
   - File system synchronization
   - Pattern-based file matching

## Testing

The project uses pytest for comprehensive testing:

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

   - Component isolation testing
   - Mock external dependencies
   - Edge case coverage
   - Type annotation verification
   - Public interface testing

2. **Integration Tests**

   - Component interaction testing
   - File system operation verification
   - JSON-RPC protocol validation
   - MCP tool functionality testing
   - Error propagation verification

3. **Performance Tests**

   - Load testing
   - File processing speed
   - Memory usage monitoring
   - Concurrent operation testing
   - Resource cleanup verification

4. **Security Tests**
   - Input validation
   - File permission verification
   - Path traversal prevention
   - Symlink handling
   - Error message validation

### Test Infrastructure

1. **Tools and Libraries**

   - pytest framework
   - pytest-asyncio
   - pytest-cov
   - pytest-xdist
   - pytest-timeout
   - pytest-randomly

2. **CI/CD Integration**

   - GitHub Actions workflow
   - Automated testing
   - Coverage reporting
   - Code quality checks
   - Security scanning

3. **Coverage Requirements**
   - 80% minimum coverage
   - Public interface testing
   - Error path verification
   - Edge case coverage
   - Documentation testing

### Pre-commit Checks

Run pre-commit script for quality checks:

```bash
python pre-commit.py
```

Checks include:

1. Test execution with coverage
2. Code formatting (black)
3. Import sorting (isort)
4. Style checking (flake8)
5. Type checking (mypy)
