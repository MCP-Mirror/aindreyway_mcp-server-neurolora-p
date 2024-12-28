# Command Help Prompt

Get help for a specific command.

## Input

- command: Name of the command to get help for

## Example

```json
{
  "command": "improve"
}
```

## Response Format

```json
{
  "title": "Command name with emoji",
  "description": "Command description",
  "usage": "Command usage syntax",
  "examples": ["Example 1", "Example 2"]
}
```

# Command Menu Prompt

Show available commands as a menu.

## Response Format

```json
[
  {
    "command": "Command name",
    "title": "Command name with emoji",
    "description": "Short description",
    "preview": "Example usage"
  }
]
```

# Command Suggestion Prompt

Suggest next actions based on command execution result.

## Input

- command: The command that was executed
- success: Whether the command succeeded
- error: Error message if command failed

## Example

```json
{
  "command": "improve",
  "success": true
}
```

## Response Format

```json
{
  "message": ["Status message"],
  "suggestions": ["Suggestion 1", "Suggestion 2"]
}
```

# Command Routing Prompt

Route natural language input to appropriate command.

## Input

- text: Natural language command to route

## Example

```json
{
  "text": "analyze my code and suggest improvements"
}
```

## Response Format

```json
{
  "command": "Selected command name",
  "confidence": 0.0-1.0,
  "reason": "Explanation for selection"
}
```

## Command Patterns

COLLECT command triggers:

- "collect code"
- "collect files"
- "collect folders"
- "собери код"
- "собрать код"
- "собери файлы"
- "собери папки"
- Keywords about viewing or gathering code

IMPROVE command triggers:

- "analyze code"
- "suggest improvements"
- "optimize"
- Keywords about code quality or improvements

REQUEST command triggers:

- "implement feature"
- "add functionality"
- "create new"
- Keywords about new features or changes

SHOWTREE command triggers:

- "show structure"
- "project tree"
- "file organization"
- Keywords about project structure
