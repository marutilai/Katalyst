# Content Reference System Debug Logging

This document describes the debug logging added to track the content reference system in Katalyst.

## Overview

The content reference system prevents LLM hallucination during file operations by storing file content with reference IDs that can be used instead of passing content through the LLM.

## Log Tags

All content reference logs use the tag `[CONTENT_REF]` for easy filtering.

## Log Levels

- **INFO**: Key operations (reference creation, usage)
- **DEBUG**: Detailed information (content size, line counts)
- **WARNING**: Potential issues (empty references)
- **ERROR**: Failures (invalid references)

## Log Points

### 1. Planner Node Start
```
[PLANNER][CONTENT_REF] Initial content_store state: {count} references
```

### 2. Read File - Reference Creation
When a file is read, a reference is created:
```
[TOOL_RUNNER][CONTENT_REF] Created content reference '{ref_id}' for file '{path}'
[TOOL_RUNNER][CONTENT_REF] Content length: {chars} chars, lines: {lines}
[TOOL_RUNNER][CONTENT_REF] Total references in store: {count}
```

### 3. Write File - LLM Choice
The system logs whether the LLM chose to use a reference or provide content directly:
```
[TOOL_RUNNER][CONTENT_REF] LLM chose to use content reference for write_to_file
# OR
[TOOL_RUNNER][CONTENT_REF] LLM provided content directly ({chars} chars) for write_to_file
```

### 4. Write File - Reference Resolution
When a content reference is used:
```
[TOOL_RUNNER][CONTENT_REF] write_to_file requested with content_ref: '{ref_id}'
[TOOL_RUNNER][CONTENT_REF] Successfully resolved content_ref '{ref_id}' to {chars} chars
[TOOL_RUNNER][CONTENT_REF] Resolved content has {lines} lines
[TOOL_RUNNER][CONTENT_REF] Writing to path: {path}
```

### 5. Write File - Invalid Reference
When an invalid reference is provided:
```
[TOOL_RUNNER][CONTENT_REF] Invalid content reference: '{ref_id}' not found in store
[TOOL_RUNNER][CONTENT_REF] Available references: [list of valid refs]
```

### 6. Task Advancement
When moving between tasks:
```
[ADVANCE_POINTER][CONTENT_REF] Content store has {count} references: [list of refs]
```

## Example Log Sequence

A typical file copy operation would produce:
```
[INFO] [TOOL_RUNNER][CONTENT_REF] Created content reference 'ref:README.md:a1b2c3d4' for file '/path/to/README.md'
[DEBUG] [TOOL_RUNNER][CONTENT_REF] Content length: 1234 chars, lines: 45
[DEBUG] [TOOL_RUNNER][CONTENT_REF] Total references in store: 1
[INFO] [TOOL_RUNNER][CONTENT_REF] LLM chose to use content reference for write_to_file
[INFO] [TOOL_RUNNER][CONTENT_REF] write_to_file requested with content_ref: 'ref:README.md:a1b2c3d4'
[INFO] [TOOL_RUNNER][CONTENT_REF] Successfully resolved content_ref 'ref:README.md:a1b2c3d4' to 1234 chars
[DEBUG] [TOOL_RUNNER][CONTENT_REF] Resolved content has 45 lines
[DEBUG] [TOOL_RUNNER][CONTENT_REF] Writing to path: README_copy.md
```

## Debugging Tips

1. **Track Reference Lifecycle**: Follow a reference from creation to usage
2. **Monitor LLM Behavior**: See if the LLM is using references when available
3. **Validate Content Integrity**: Compare character/line counts between creation and resolution
4. **Identify Missing References**: Check available references when resolution fails

## Log Filtering

To see only content reference logs:
```bash
grep "CONTENT_REF" katalyst.log
```

To see only reference creation:
```bash
grep "Created content reference" katalyst.log
```

To see only reference usage:
```bash
grep "resolved content_ref" katalyst.log
```