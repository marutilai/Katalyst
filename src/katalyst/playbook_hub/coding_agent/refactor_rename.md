# Playbook: Unified Refactoring - Renaming Identifiers and Paths

Description: This comprehensive playbook provides a systematic approach to safely rename any identifier or path in a codebase. It handles functions, classes, variables, files, and directories with type-specific strategies while maintaining code integrity and preventing runtime errors.

**Input Requirements:**
- `target_type`: The type of element to rename (function | class | variable | file | directory)
- `old_name`: The current name/path of the target
- `new_name`: The desired new name/path
- `scope` (optional, for variables): Scope of the variable (local | instance | class | global)
- `module_path` (optional): Specific module/directory to narrow the search scope

**Output:** A fully refactored codebase with all occurrences renamed, including:
- Target definitions/declarations
- All references and usages
- Import statements
- Test references
- Documentation mentions
- Path references (for files/directories)

## Step 1: Validate Input and Locate Target

**Goal:** Verify the target exists and understand its exact location and context.

### Type-Specific Location Strategies:

#### Functions:
- Use `search_files` with pattern `def {old_name}(` to find function definitions
- Check for async functions: `async def {old_name}(`
- Note decorators, type hints, and docstrings

#### Classes:
- Use `search_files` with pattern `class {old_name}[:(]` to find class definitions
- Check for inheritance patterns and metaclasses
- Note class decorators and nested classes

#### Variables:
- **Global/Module-level:** Search for `{old_name} =` at top level
- **Instance variables:** Search for `self.{old_name}` in `__init__` methods
- **Class variables:** Search for `{old_name} =` within class bodies
- **Local variables:** Context-dependent within specific functions

#### Files:
- Use `list_files` to verify file exists at the given path
- Record file extension and parent directory
- Check if it's a module (`__init__.py` considerations)

#### Directories:
- Use `list_files` to verify directory exists
- Check if it's a Python package (contains `__init__.py`)
- List all files within the directory for import analysis

## Step 2: Analyze Usage Patterns

**Goal:** Create a comprehensive map of all references to understand the refactoring scope.

### Type-Specific Usage Analysis:

#### Functions:
- Direct calls: `{old_name}(`
- Imports: `from module import {old_name}`
- Aliased imports: `import {old_name} as alias`
- Passed as arguments: `callback={old_name}`
- Decorators using the function

#### Classes:
- Instantiation: `{old_name}(`
- Inheritance: `class Child({old_name}):`
- Type hints: `param: {old_name}`, `-> {old_name}`
- Class method calls: `{old_name}.method()`
- Metaclass usage: `metaclass={old_name}`

#### Variables:
- **Global:** All files importing the module
- **Instance:** `self.{old_name}` and `obj.{old_name}` patterns
- **Class:** `ClassName.{old_name}` and inheritance considerations
- **Local:** Within the function scope only

#### Files:
- Import statements: `from path.to.{old_name} import`
- Relative imports: `from .{old_name} import`
- Dynamic imports: `importlib.import_module('path.to.{old_name}')`
- File path references in strings

#### Directories:
- Module imports: `import {old_name}`
- Package imports: `from {old_name} import`
- Submodule imports: `from {old_name}.submodule import`
- Path references in configuration files

## Step 3: Check String References

**Goal:** Identify string-based references that require special handling.

### Common String Reference Patterns:
- Dynamic imports: `getattr(module, '{old_name}')`
- Reflection: `hasattr(obj, '{old_name}')`
- Configuration files: JSON, YAML, TOML with identifier names
- API endpoints: URL patterns containing the name
- Logging statements: Log messages mentioning the identifier
- Documentation: Docstrings and comments
- File paths: For file/directory renames
- Environment variables: Variable names in `.env` files

## Step 4: Create Replacement Strategy

**Goal:** Plan the order of replacements to avoid conflicts and maintain consistency.

### Replacement Order:
1. **Update imports first** (to avoid breaking dependencies)
2. **Rename the target** (definition/declaration/path)
3. **Update all references** (calls, usages, type hints)
4. **Update string references** (configuration, logging)
5. **Update tests** (test names, assertions)
6. **Update documentation** (comments, docstrings, markdown)

### Type-Specific Considerations:
- **Files/Directories:** Use `bash` tool with `mv` command
- **Code elements:** Use `edit` or `multiedit` for replacements
- **Import ordering:** Maintain PEP 8 import order

## Step 5: Execute Rename - Target Definition

**Goal:** Rename the primary target while preserving all attributes.

### Type-Specific Execution:

#### Functions:
```python
# Replace: def {old_name}(
# With: def {new_name}(
```

#### Classes:
```python
# Replace: class {old_name}
# With: class {new_name}
```

#### Variables:
```python
# Replace patterns based on scope:
# Global: {old_name} =
# Instance: self.{old_name}
# Class: (within class body) {old_name} =
```

#### Files/Directories:
```bash
# Use bash tool with mv command
# Example: bash("mv path/to/{old_name}.py path/to/{new_name}.py")
```

## Step 6: Update All Import Statements

**Goal:** Ensure all imports reference the renamed target correctly.

### Import Update Patterns:

#### For Functions/Classes:
- `from module import {old_name}` → `from module import {new_name}`
- `from module import {old_name} as alias` → `from module import {new_name} as alias`
- `from module import x, {old_name}, y` → `from module import x, {new_name}, y`

#### For Files:
- `from path.to.{old_name} import` → `from path.to.{new_name} import`
- `import path.to.{old_name}` → `import path.to.{new_name}`

#### For Directories:
- `import {old_name}` → `import {new_name}`
- `from {old_name} import` → `from {new_name} import`
- `from {old_name}.submodule import` → `from {new_name}.submodule import`

## Step 7: Update All References

**Goal:** Replace all usages of the renamed target throughout the codebase.

### Reference Update Patterns:

#### Functions:
- Function calls: `{old_name}(args)` → `{new_name}(args)`
- Callbacks: `callback={old_name}` → `callback={new_name}`
- Decorators: `@{old_name}` → `@{new_name}`

#### Classes:
- Instantiation: `{old_name}()` → `{new_name}()`
- Inheritance: `class Child({old_name}):` → `class Child({new_name}):`
- Type hints: `: {old_name}` → `: {new_name}`

#### Variables:
- Based on scope, update all occurrences
- Preserve attribute access patterns

#### Files/Directories:
- Update any hardcoded path strings
- Update relative import paths

## Step 8: Update Tests

**Goal:** Ensure all tests reference and test the renamed target correctly.

### Test Update Strategies:
- Test function names: `test_{old_name}_*` → `test_{new_name}_*`
- Test class names: `Test{OldName}` → `Test{NewName}`
- Assertions on names: String assertions, mock names
- Fixture names: `{old_name}_fixture` → `{new_name}_fixture`
- Parametrized test IDs containing the name
- Test file names: `test_{old_name}.py` → `test_{new_name}.py`

## Step 9: Update Documentation and Comments

**Goal:** Ensure all documentation accurately reflects the rename.

### Documentation Updates:
- Docstrings mentioning the target
- README files with usage examples
- API documentation
- Code comments referencing the target
- CHANGELOG entries (add note about rename)
- Migration guides
- Configuration examples

## Step 10: Update String References

**Goal:** Handle dynamic and configuration-based references.

### String Reference Updates:
- Configuration files (JSON, YAML, TOML)
- Environment variable names
- Dynamic import strings
- Logging messages
- Error messages
- CLI command names
- API endpoint paths

## Step 11: Comprehensive Verification

**Goal:** Ensure the refactoring was successful and complete.

### Verification Steps:
1. **Syntax Check:**
   - Run linting tools (pylint, flake8, ruff)
   - Check for syntax errors

2. **Import Verification:**
   - Verify no import errors
   - Check for circular imports

3. **Type Checking:**
   - Run mypy or type checker
   - Verify type hints are consistent

4. **Test Suite:**
   - Run full test suite
   - Verify all tests pass

5. **Final Search:**
   - Search for `{old_name}` to ensure no occurrences remain
   - Review any remaining matches for false positives

6. **Documentation Build:**
   - Build documentation if applicable
   - Verify no broken references

## Step 12: Generate Summary Report

**Goal:** Provide a comprehensive summary of all changes.

### Report Contents:
- Total files modified by category
- Breakdown of changes:
  - Definition/declaration updates: X
  - Import updates: Y
  - Reference updates: Z
  - Test updates: A
  - Documentation updates: B
  - String reference updates: C
- Any skipped references with justification
- Verification results:
  - Linting status
  - Type checking status
  - Test results
- Recommendations for manual review

## Error Handling and Edge Cases

### General Considerations:
- **Name Conflicts:** Check if new name already exists
- **Partial Matches:** Use word boundaries to avoid substring replacements
- **Case Sensitivity:** Maintain original casing patterns
- **Reserved Keywords:** Ensure new name isn't a language keyword

### Type-Specific Edge Cases:

#### Functions:
- Overloaded functions (multiple definitions)
- Nested functions
- Lambda functions assigned to the name
- Generator functions

#### Classes:
- Inner/nested classes
- Multiple inheritance
- Metaclass conflicts
- Class vs instance method naming

#### Variables:
- Shadowing in nested scopes
- Global vs local conflicts
- Property getters/setters

#### Files/Directories:
- Cross-platform path separators
- Symlinks and aliases
- Git tracking considerations
- Binary files with the same name

## Rollback Strategy

If issues arise during refactoring:
1. Keep track of all modified files
2. Use version control to review changes
3. Ability to revert specific file changes
4. Document any manual interventions required

## Strict Execution Requirements

- **Never assume** a single usage pattern - always search comprehensively
- **Preserve formatting** - maintain existing code style and indentation
- **Atomic changes** - ensure all related changes are made together
- **Test continuously** - run relevant tests after each major step
- **Document decisions** - note any ambiguous cases or exceptions
- **Respect boundaries** - don't rename external dependencies
- **Version control** - ensure changes are tracked properly
- **User confirmation** - get approval for high-risk changes