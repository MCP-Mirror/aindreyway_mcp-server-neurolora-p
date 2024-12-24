# Project TODO List

This document outlines current issues and improvements needed in the MCP Server Neurolorap project. Each item is categorized and prioritized for easy reference by AI assistants.

## Issue Categories

- 🚨 WARNING: Potential problems that need attention
- 🔧 IMPROVE: Optimization and enhancement opportunities
- 🎯 PRIORITY: High/Medium/Low importance tasks
- ⚡ EFFORT: Small/Medium/Large implementation effort

## Active Issues

- [ ] Issue 1: Performance Optimization
- [ ] Issue 2: Logging Level Optimization
- [ ] Issue 3: Request ID Management
- [ ] Issue 4: Logging Level Correction

### 1. Performance Optimization

**Type**: 🔧 IMPROVE | 🎯 PRIORITY: High | ⚡ EFFORT: Medium

**Problem**:

- Excessive use of `os.sync()` and `time.sleep()`
- Unnecessary filesystem synchronization
- Performance degradation

**Required Changes**:

1. Remove redundant sync calls:

```python
# Before
os.sync()
time.sleep(1)
if os.path.exists(path):
    # code

# After
os.makedirs(path, exist_ok=True)
# Continue with operations
```

2. Update directory operations to use native Python functionality
3. Revise test suite to remove unnecessary waits

**Files to Check**:

- src/mcp_server_neurolorap/storage.py
- src/mcp_server_neurolorap/collector.py

### 2. Logging Level Optimization

**Type**: 🔧 IMPROVE | 🎯 PRIORITY: Medium | ⚡ EFFORT: Small

**Problem**:

- Excessive INFO level logging
- Log clutter in should_ignore_file
- Performance impact during large scans

**Required Changes**:

1. Adjust logging levels:

```python
# Before
logger.info(f"Walking directory: {path}")

# After
logger.debug(f"Walking directory: {path}")
```

2. Define clear logging hierarchy:
   - ERROR: Only for actual errors that need immediate attention
   - WARNING: For concerning but non-critical issues
   - INFO: For significant events (start/end of operations)
   - DEBUG: For detailed operational data

**Files to Check**:

- src/mcp_server_neurolorap/collector.py (should_ignore_file function)
- All files using logger

### 3. Request ID Management

**Type**: 🚨 WARNING | 🎯 PRIORITY: Low | ⚡ EFFORT: Small

**Problem**:

- Unsynchronized request_id counter in JsonRpcTerminal
- Potential race conditions in concurrent scenarios

**Required Changes**:

1. Implement thread-safe counter:

```python
# Before
self.request_id += 1

# After
from itertools import count
self._counter = count()
self.request_id = next(self._counter)
```

2. Document concurrency limitations
3. Plan for future concurrent architecture

**Files to Check**:

- src/mcp_server_neurolorap/terminal.py

### 4. Logging Level Correction

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
