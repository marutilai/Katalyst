# Playbook: Safe Dependency Update and Migration

Description: This playbook provides a systematic approach to updating project dependencies safely. It covers analyzing current dependencies, checking for updates and vulnerabilities, handling breaking changes, and ensuring the application remains stable throughout the upgrade process.

**Input Requirements:**
- `upgrade_type`: Type of upgrade (patch | minor | major | security | all)
- `target_dependencies` (optional): Specific dependencies to upgrade (if not all)
- `exclude_dependencies` (optional): Dependencies to exclude from upgrade
- `dry_run` (optional): Whether to just analyze without making changes (default: false)

**Output:** A fully upgraded project with:
- Updated dependency versions
- Fixed deprecation warnings
- Resolved breaking changes
- Comprehensive upgrade documentation
- Rollback instructions if needed

## Step 1: Analyze Current Dependencies

**Goal:** Create a comprehensive map of all project dependencies and their current state.

**Method:**
- Identify dependency files based on project type:
  - Python: `pyproject.toml`, `requirements.txt`, `Pipfile`
  - JavaScript: `package.json`, `yarn.lock`, `package-lock.json`
  - Ruby: `Gemfile`, `Gemfile.lock`
  - Go: `go.mod`, `go.sum`
  - Rust: `Cargo.toml`, `Cargo.lock`
- Use `read_file` to parse dependency files
- Extract:
  - Direct dependencies vs transitive dependencies
  - Version constraints (pinned, ranges, latest)
  - Development vs production dependencies
  - Optional dependencies
- Create dependency tree showing relationships

## Step 2: Check for Available Updates

**Goal:** Identify all available updates and categorize them by risk level.

**Method:**
- Use language-specific commands to check updates:
  ```bash
  # Python
  pip list --outdated
  poetry show --outdated
  
  # JavaScript
  npm outdated
  yarn outdated
  
  # Ruby
  bundle outdated
  ```
- For each dependency with updates:
  - Current version
  - Latest version available
  - Update type (patch/minor/major)
  - Release date of latest version
- Categorize updates:
  - **Patch (1.2.3 → 1.2.4)**: Bug fixes, safe
  - **Minor (1.2.3 → 1.3.0)**: New features, usually safe
  - **Major (1.2.3 → 2.0.0)**: Breaking changes, risky

## Step 3: Security Vulnerability Analysis

**Goal:** Identify and prioritize security vulnerabilities in dependencies.

**Method:**
- Run security audit tools:
  ```bash
  # Python
  pip-audit
  safety check
  
  # JavaScript
  npm audit
  yarn audit
  
  # Ruby
  bundle-audit check
  ```
- For each vulnerability:
  - Severity level (critical/high/medium/low)
  - CVE identifier
  - Affected versions
  - Fixed versions
  - Exploit details
- Prioritize security updates regardless of breaking changes

## Step 4: Analyze Breaking Changes

**Goal:** Understand the impact of major version updates.

**Method:**
For each major update:
- Search for changelog/release notes:
  - GitHub releases page
  - CHANGELOG.md in repository
  - Documentation migration guides
- Use `web_fetch` if needed to get release information
- Identify:
  - Removed features/APIs
  - Changed function signatures
  - New required configurations
  - Behavioral changes
- Search codebase for usage of affected APIs:
  ```bash
  # Find usage of deprecated features
  grep -r "deprecated_function" --include="*.py"
  ```

## Step 5: Create Upgrade Strategy

**Goal:** Plan the order and grouping of updates to minimize risk.

**Method:**
Create upgrade groups:

1. **Security Updates** (Highest Priority):
   - Critical vulnerabilities first
   - May require major version jumps

2. **Patch Updates** (Low Risk):
   - Bug fixes only
   - Can usually be batched

3. **Minor Updates** (Medium Risk):
   - New features, backwards compatible
   - Test after batch updating

4. **Major Updates** (High Risk):
   - Update one at a time
   - Extensive testing required
   - May need code changes

Document upgrade order considering:
- Dependency relationships
- Testing requirements
- Rollback complexity

## Step 6: Create Backup and Rollback Plan

**Goal:** Ensure ability to revert if issues arise.

**Method:**
- Create backup of current dependency files:
  ```bash
  cp requirements.txt requirements.txt.backup
  cp package-lock.json package-lock.json.backup
  ```
- Document current working versions
- Create git branch for upgrade work:
  ```bash
  git checkout -b dependency-upgrade-$(date +%Y%m%d)
  ```
- Document rollback procedures:
  - How to restore dependency files
  - How to clear caches
  - How to reinstall exact versions

## Step 7: Execute Patch and Minor Updates

**Goal:** Apply low-risk updates first to establish baseline.

**Method:**
- Update patch versions first:
  ```bash
  # Python
  poetry update --patch
  
  # JavaScript
  npm update --save
  ```
- Run test suite after updates:
  ```bash
  pytest
  npm test
  ```
- Check for warnings or deprecations
- Commit if tests pass:
  ```bash
  git add -u
  git commit -m "Update patch and minor dependency versions"
  ```

## Step 8: Execute Major Updates Individually

**Goal:** Carefully update each major version with code changes.

**Method:**
For each major update:

1. **Update single dependency**:
   ```bash
   # Python
   poetry add package@^2.0.0
   
   # JavaScript
   npm install package@2.0.0
   ```

2. **Fix breaking changes**:
   - Search for all usage of the package
   - Update import statements
   - Modify function calls per changelog
   - Update configuration files

3. **Run tests**:
   - Unit tests
   - Integration tests
   - Manual testing of affected features

4. **Fix deprecation warnings**:
   - Address all warnings before proceeding
   - Update to recommended new APIs

5. **Commit individual update**:
   ```bash
   git add -A
   git commit -m "Upgrade {package} to v2.0.0"
   ```

## Step 9: Update Development Dependencies

**Goal:** Ensure development tools are current.

**Method:**
- Update test frameworks
- Update linters and formatters
- Update build tools
- Update type checkers
- These often have fewer breaking changes
- Can be more aggressive with updates

## Step 10: Update Lock Files and Clean Cache

**Goal:** Ensure reproducible installs with updated dependencies.

**Method:**
- Regenerate lock files:
  ```bash
  # Python
  poetry lock
  pip freeze > requirements.txt
  
  # JavaScript
  npm install  # Updates package-lock.json
  yarn install # Updates yarn.lock
  ```
- Clean dependency caches:
  ```bash
  # Python
  pip cache purge
  
  # JavaScript
  npm cache clean --force
  ```
- Verify clean install:
  - Delete virtual environment/node_modules
  - Reinstall from lock files
  - Run tests again

## Step 11: Update Documentation

**Goal:** Document the upgrade process and any changes required.

**Method:**
Create/Update UPGRADE.md with:

1. **Summary of Updates**:
   - List all updated packages with version changes
   - Highlight major updates
   - Note security fixes

2. **Breaking Changes**:
   - Code changes required
   - Configuration changes
   - Behavioral changes

3. **New Features Available**:
   - New APIs now available
   - Performance improvements
   - New configuration options

4. **Migration Instructions**:
   - Steps for other developers
   - Environment setup changes
   - Required manual interventions

Update other documentation:
- README.md with new version requirements
- API documentation for changed interfaces
- Configuration examples

## Step 12: Comprehensive Testing

**Goal:** Ensure application stability with updated dependencies.

**Method:**
1. **Automated Tests**:
   - Run full test suite
   - Check code coverage hasn't decreased
   - Run performance benchmarks

2. **Manual Testing**:
   - Test critical user workflows
   - Check integration points
   - Verify external API interactions

3. **Environment Testing**:
   - Test in development environment
   - Test in staging environment
   - Load testing if applicable

4. **Regression Testing**:
   - Test previously fixed bugs
   - Check edge cases
   - Verify data migrations

## Step 13: Generate Upgrade Report

**Goal:** Provide comprehensive summary of the upgrade process.

**Method:**
Create report including:

1. **Upgrade Summary**:
   - Total dependencies updated
   - Security vulnerabilities fixed
   - Major version upgrades completed

2. **Risk Assessment**:
   - Remaining outdated dependencies (with reasons)
   - Known issues or limitations
   - Performance impact analysis

3. **Testing Results**:
   - Test suite results
   - Performance benchmarks
   - Manual testing checklist

4. **Rollback Instructions**:
   - How to revert if issues found in production
   - Specific version pins for critical dependencies

5. **Next Steps**:
   - Recommended monitoring
   - Future upgrade timeline
   - Technical debt items

## Error Handling and Recovery

### Common Issues:
- **Dependency Conflicts**: Use resolution strategies
- **Missing Dependencies**: Check for new peer dependencies
- **Build Failures**: Clear caches and rebuild
- **Test Failures**: May need test updates for new APIs
- **Performance Degradation**: Profile and compare

### Recovery Procedures:
1. Revert to backup dependency files
2. Clear all caches
3. Delete and recreate virtual environment
4. Reinstall from backup lock files
5. Verify working state before proceeding

## Best Practices

### General Principles:
- Update regularly to avoid large jumps
- Prioritize security updates
- Test thoroughly at each step
- Document all changes
- Keep dependencies minimal

### Version Constraints:
- Use appropriate version specifiers
- Pin major versions in production
- Allow patch updates automatically
- Review minor updates before applying

### Team Coordination:
- Communicate updates to team
- Coordinate major updates
- Share upgrade documentation
- Update CI/CD configurations

## Strict Execution Requirements

- Never update all dependencies at once without analysis
- Always create backups before starting
- Test after each significant update
- Document all manual interventions required
- Ensure clean install works from lock files
- Update all environments consistently
- Monitor application after deployment
- Keep security updates separate from feature updates
- Maintain ability to rollback at any stage