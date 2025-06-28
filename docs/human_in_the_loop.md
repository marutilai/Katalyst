# Human-in-the-Loop Plan Verification

Katalyst now includes interactive plan verification, allowing users to review and approve plans before execution.

## How It Works

When Katalyst generates a plan, it presents it for your approval:

```
============================================================
🤖 KATALYST PLAN VERIFICATION
============================================================

Task: Build a web scraper

Generated Plan:
  1. Set up project structure
  2. Implement scraping logic
  3. Add data parsing
  4. Create storage system
  5. Add error handling
  6. Write tests

------------------------------------------------------------

Do you approve this plan?
- Type 'yes' or 'y' to approve and continue
- Type 'no' or provide feedback for a better plan
- Type 'cancel' to stop

Your response: 
```

## Response Options

- **Approve**: `yes` or `y` - Execute the plan
- **Feedback**: `no` or direct feedback - Generate new plan with your input
- **Cancel**: `cancel` - Stop operation

## Example Feedback Loop

```
Your response: Add rate limiting and respect robots.txt

[Katalyst incorporates feedback and shows revised plan]
```

## Auto-Approve Mode

Skip verification for automated workflows:

```bash
katalyst --auto-approve "Build a calculator"
```

Or set environment variable: `KATALYST_AUTO_APPROVE=true`

## Benefits

- Ensure plans match your expectations
- Catch issues before execution
- Iterate until the plan is perfect
- Maintain control over complex operations

## Configuration

- Command line: `--auto-approve`
- Environment: `KATALYST_AUTO_APPROVE=true`
- Programmatic: `auto_approve=True` in state