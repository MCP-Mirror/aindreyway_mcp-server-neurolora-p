# Project TODO List

This document outlines current issues and improvements needed in the MCP Server Neurolorap project. Each item is categorized and prioritized for easy reference by AI assistants.

## Issue Categories

- 🚨 WARNING: Potential problems that need attention
- 🔧 IMPROVE: Optimization and enhancement opportunities
- 🎯 PRIORITY: High/Medium/Low importance tasks
- ⚡ EFFORT: Small/Medium/Large implementation effort

## Active Issues

- [ ] Issue 1: Logging Level Correction

### 1. Logging Level Correction

**Type**: 🚨 WARNING | 🎯 PRIORITY: Medium | ⚡ EFFORT: Small

**Problem**:

- Incorrect use of ERROR level for routine operations
- Misleading severity levels in logs

**Required Changes**:

1. Update logging levels:

```python
# Before
logger.error(f"Tool call: {name}")

# After
logger.info(f"Tool call: {name}")
# or
logger.debug(f"Tool call: {name}")
```

2. Review and correct all logging statements
3. Update log monitoring configurations

**Files to Check**:

- src/mcp_server_neurolorap/server.py
- All files using logger.error()

## Implementation Guidelines

1. **Testing**:

   - Add unit tests for each fix
   - Verify logging output
   - Test performance improvements
   - Document test cases

2. **Documentation**:

   - Update docstrings
   - Add inline comments for complex changes
   - Update PROJECT_SUMMARY.md if needed

3. **Code Quality**:
   - Follow project's style guide
   - Use type hints
   - Maintain modular architecture

## Notes for AI Assistants

1. Before making changes:

   - Read PROJECT_SUMMARY.md
   - Check existing implementations
   - Consider impact on other components

2. When implementing fixes:

   - Make atomic, focused changes
   - Update tests accordingly
   - Follow error handling patterns
   - Maintain consistent logging

3. After changes:
   - Update this TODO.md
   - Document any new issues discovered
   - Update progress tracking
