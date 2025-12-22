# Agent Guide for the Skills Repository

This repository contains Claude Code skills/plugins for various utilities. It's a monorepo with two main skill packages: `plex` and `code-health`.

## Project Structure

```
skills/
├── plex/              # Plex media server query skill
│   ├── scripts/       # CLI tools (plex-movie, plex-tv, plex-genres)
│   ├── examples/      # Example query patterns
│   ├── SKILL.md       # Skill documentation (contains comprehensive usage guide)
│   ├── pyproject.toml # Python project config
│   └── README.md      # User-facing documentation
├── code-health/       # Code health analysis skill
│   ├── scripts/       # Health analysis tools (health.py, gofuncs.go, pyfuncs.py, jsfuncs.js)
│   └── SKILL.md       # Skill documentation
└── .claude-plugin/    # Plugin metadata for marketplace
```

## The Two Skills

### 1. Plex (`plex/`)

A Python-based skill for querying Plex Media Server libraries. Users can ask natural language questions about their media library.

**Key files:**

- `plex/scripts/plex-movie` - Movie search CLI
- `plex/scripts/plex-tv` - TV show search CLI
- `plex/scripts/plex-genres` - Genre discovery CLI
- `plex/SKILL.md` - Comprehensive skill guide (read this first for usage details)
- `plex/examples/` - Complex query examples

**Dependencies:**

- `plexapi>=4.15.0`
- Python 3.8+

**Environment variables required:**

- `PLEX_URL` - Plex server URL (e.g., `http://192.168.1.100:32400`)
- `PLEX_TOKEN` - Plex authentication token

**Optional config:**

- `PLEX_DEFAULT_MOVIE_LIBRARIES`
- `PLEX_DEFAULT_TV_LIBRARIES`
- `PLEX_DEFAULT_LIMIT` (default: 20)
- `PLEX_CACHE_EXPIRY` (default: 3600)

**Key commands (for testing):**

```bash
# From the plex/ directory
python scripts/plex-genres              # List available genres
python scripts/plex-movie --help        # Movie search options
python scripts/plex-tv --help           # TV search options
```

**All scripts output JSON by default** - optimized for LLM consumption.

### 2. Code Health (`code-health/`)

A multi-language codebase health analyzer that detects issues like large files, test gaps, duplicates, dead code, and documentation problems.

**Key files:**

- `code-health/scripts/health.py` - Main health analyzer (auto-detects project type)
- `code-health/scripts/gofuncs.go` - Go function analyzer (AST-based)
- `code-health/scripts/pyfuncs.py` - Python function analyzer (AST-based)
- `code-health/scripts/jsfuncs.js` - JavaScript/TypeScript function analyzer (regex-based)
- `code-health/SKILL.md` - Comprehensive skill guide

**Dependencies:**

- Python 3.8+ (for health.py)
- Go (optional, for gofuncs)
- Node.js (optional, for jsfuncs)
- `rg` (ripgrep), `fd`, `git` (optional, for better results)
- `staticcheck` (optional, for Go projects)

**Key commands (for testing):**

```bash
# From the code-health/ directory
python scripts/health.py --json /path/to/project          # Full scan with JSON output
python scripts/health.py --check tests --json [directory]  # Specific check
go run scripts/gofuncs.go -dir /path/to/project          # Go function analysis
python scripts/pyfuncs.py --dir /path/to/project          # Python function analysis
node scripts/jsfuncs.js --dir /path/to/project            # JS/TS function analysis
```

**Checks available:**

- `size` - Large files, function counts, git churn
- `tests` - Coverage gaps, missing test files
- `dupes` - Duplicate code patterns
- `dead` - Legacy markers, unused exports, stale code
- `docs` - Undocumented exports, missing READMEs

## Common Patterns

### Python Scripts (both plex and code-health)

**Error handling:** All Python scripts output JSON error objects to stderr:

```json
{
  "error": "ErrorType",
  "message": "Human-readable message",
  "details": "Technical details",
  "recovery": "Suggested fix"
}
```

**Configuration loading pattern:**

```python
def load_config() -> Dict[str, Any]:
    config = {
        "url": os.getenv("ENV_VAR", "default_value"),
        # ...
    }
    if not config["url"]:
        return None  # Or print error and exit
    return config
```

**Argument parsing:** Use `argparse` with `argparse.RawDescriptionHelpFormatter` for clean help text.

### Code Health Tools

**Function analyzer output format** (consistent across all languages):

```
file:line:type:exported:name:class_or_receiver:signature:decorators
```

- `type`: `f`=function, `m`=method, `a`=arrow (JS), `c`=constructor (JS), `s`=staticmethod (py), `p`=property (py)
- `exported`: `y`=public, `n`=private

**Project type detection logic (health.py):**

- Go: `go.mod` exists OR `.go` files present
- Python: `pyproject.toml` OR `setup.py` exists
- TypeScript: `tsconfig.json` exists
- JavaScript: `package.json` exists

## File Organization Conventions

### SKILL.md Format

Each skill has a `SKILL.md` file that follows this format:

```markdown
---
name: skill-name
description: Brief description of when to use this skill
version: X.Y.Z
---

# Skill Name

Detailed explanation of the skill, usage patterns, examples, etc.
```

**The SKILL.md files are the authoritative documentation** - they contain:

- When to use the skill
- Available tools and their parameters
- Workflow for answering queries
- Error handling patterns
- Best practices

### Directory Structure

- Each skill is self-contained with its own `scripts/` directory
- Executable scripts use shebang: `#!/usr/bin/env python3` or `#!/usr/bin/env node`
- Scripts are CLI-first tools that output JSON
- Examples are in `examples/` subdirectory within each skill

## Working with This Repository

### Adding a New Skill

1. Create a new directory for the skill (e.g., `new-skill/`)
2. Add a `SKILL.md` file following the format above
3. Implement CLI tools in `scripts/` subdirectory
4. Update `.claude-plugin/marketplace.json` to register the new skill
5. Add a `README.md` for user-facing documentation if needed
6. Add an `examples/` directory with usage examples

### Modifying Existing Skills

**Before editing:**

- Read the `SKILL.md` file for the skill first
- Read existing scripts to understand patterns (JSON output, error handling)
- Check how other similar scripts are implemented

**Testing changes:**

```bash
# For plex skill
cd plex
python scripts/plex-genres
python scripts/plex-movie --help
python scripts/plex-tv --help

# For code-health skill
cd code-health
python scripts/health.py --json /path/to/test/project
```

### Code Style

**Python:**

- Use type hints (`from typing import List, Dict, Any, Optional`)
- Consistent indentation (4 spaces)
- Docstrings for functions using triple quotes
- Error objects printed to stderr as JSON

**JavaScript:**

- ES6+ syntax
- Consistent indentation (2 or 4 spaces - check existing files)
- Use `#!/usr/bin/env node` shebang

**Go:**

- Standard Go formatting (`gofmt`)
- Clear, idiomatic Go code

## Important Gotchas

1. **Environment variables:** The Plex skill requires `PLEX_URL` and `PLEX_TOKEN` to be set. Without these, scripts will exit with JSON errors.

2. **Executable permissions:** Scripts in `scripts/` directories should be executable (`chmod +x`).

3. **JSON output:** All CLI tools output JSON by default. This is intentional for LLM consumption. Human-readable output is secondary.

4. **Missing dependencies:** The code-health tools will still work if optional tools like `rg`, `fd`, `staticcheck` are missing - they'll just report them as missing tools and use fallback methods.

5. **Cross-platform path handling:** Python scripts use `os.path.join()` for path construction. JavaScript uses `path.join()`.

6. **SKILL.md is authoritative:** When in doubt, consult the `SKILL.md` file for each skill - it contains the most up-to-date usage information.

## Repository Metadata

- **Owner:** lepinkainen
- **Repository:** <https://github.com/lepinkainen/skills>
- **Plugin manifest:** `.claude-plugin/marketplace.json`

## Quick Reference for Common Tasks

### Testing Plex Skill

```bash
cd plex
export PLEX_URL="http://your-server:32400"
export PLEX_TOKEN="your-token"
python scripts/plex-genres
python scripts/plex-movie --genre action --limit 5
```

### Testing Code Health Skill

```bash
cd code-health
python scripts/health.py --json /path/to/project
python scripts/health.py --check size --json /path/to/project
```

### Analyzing Functions

```bash
cd code-health
# Go
go run scripts/gofuncs.go -dir /path/to/go/project

# Python
python scripts/pyfuncs.py --dir /path/to/python/project

# JavaScript
node scripts/jsfuncs.js --dir /path/to/js/project
```

### Adding New Scripts to Existing Skills

1. Follow the existing patterns (JSON output, argparse, error handling)
2. Add to the appropriate `scripts/` directory
3. Make executable: `chmod +x scripts/your-script`
4. Document usage in the skill's `SKILL.md`
5. Add examples to `examples/` if relevant
