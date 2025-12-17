---
name: code-health
description: Analyze codebase health - large files, test coverage gaps, duplicate code, dead/legacy code, and documentation issues. Use when asked to scan, audit, or assess code quality, find refactoring targets, or identify technical debt.
---

# Code Health Analysis

Run `scripts/health.py` to analyze codebase health. The script auto-detects project type (Go, Python, JS/TS) and runs appropriate checks.

## Usage

```bash
# Full scan (all checks)
python /path/to/skill/scripts/health.py [directory]

# Specific checks
python /path/to/skill/scripts/health.py --check size [directory]
python /path/to/skill/scripts/health.py --check tests [directory]
python /path/to/skill/scripts/health.py --check dupes [directory]
python /path/to/skill/scripts/health.py --check dead [directory]
python /path/to/skill/scripts/health.py --check docs [directory]

# JSON output for programmatic use
python /path/to/skill/scripts/health.py --json [directory]
```

## Checks

| Check | Description |
|-------|-------------|
| `size` | Large files, function counts, git churn |
| `tests` | Coverage gaps, missing test files, test quality |
| `dupes` | Duplicate function names, similar patterns |
| `dead` | Legacy markers, unused exports, stale code |
| `docs` | Undocumented exports, missing READMEs |

## Output

The script outputs structured findings with severity levels:

- 🔴 **critical**: Immediate attention needed
- 🟡 **warning**: Should address soon  
- 🟢 **info**: Nice to fix

Each finding includes file path, line number, description, and suggested action.

## Requirements

Required: `python3`
Optional (for better results): `rg` (ripgrep), `fd`, `git`, `go` (for Go projects), `staticcheck`

Missing tools are reported but don't block execution.
