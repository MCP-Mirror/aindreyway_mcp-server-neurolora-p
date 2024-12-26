# Project Structure Reporter Implementation

## Changes

- Add new module `project_structure_reporter.py` for analyzing project structure
- Integrate with MCP server as a new tool
- Add automatic report generation functionality

## Technical Details

### Core Components

1. ProjectStructureReporter class:

   - File and directory analysis
   - Metrics calculation
   - Report generation
   - Ignore patterns support

2. MCP Tool Integration:
   - New tool: "project-structure-reporter"
   - Report generation on demand
   - Automatic updates support

### Features

1. File Analysis:

   - Size measurement (bytes/KB)
   - Line counting (excluding empty lines)
   - Token estimation (4 chars ≈ 1 token)
   - Large file detection (>1MB)
   - Code complexity indicators (>300 lines)

2. Report Generation:
   - Markdown format
   - File metrics
   - Project totals
   - Visual indicators
   - Timestamp and metadata

### Implementation Plan

1. Core Module Development:

   ```python
   class ProjectStructureReporter:
       def analyze_project_structure(self) -> dict
       def should_ignore(self, path: Path) -> bool
       def count_lines(self, filepath: Path) -> int
       def generate_markdown_report(self, data: dict, output: Path)
   ```

2. Integration Steps:

   - Add module to src/mcp_server_neurolorap/
   - Update server.py to include new tool
   - Add configuration options
   - Implement automatic updates

3. Testing Requirements:
   - Unit tests for core functionality
   - Integration tests for MCP tool
   - Performance testing for large projects

## Testing

- Unit tests for all core functions
- Integration tests for MCP tool
- Edge cases:
  - Empty files
  - Binary files
  - Large files
  - Special characters in paths
  - Various file types

## Related Issues

- Need for project structure analysis
- Code complexity monitoring
- Resource usage tracking

## Notes

Report will be stored in .neurolora directory with format:

```markdown
# Project Structure Report

Generated: [timestamp]

## Files

- path/to/file.py (size, tokens, lines) [indicators]

## Summary

- Total size
- Total lines
- Total tokens
- Large files count

## Notes

- Explanation of indicators
- Metric calculations
- Exclusion rules
```
