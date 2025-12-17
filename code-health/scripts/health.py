#!/usr/bin/env python3
"""Code health analyzer - detects large files, test gaps, duplicates, dead code, and doc issues."""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ProjectType(Enum):
    GO = "go"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


@dataclass
class Finding:
    check: str
    severity: str
    file: str
    line: Optional[int]
    message: str
    action: str

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CheckResult:
    name: str
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


@dataclass
class HealthReport:
    directory: str
    project_type: str
    checks: list[CheckResult] = field(default_factory=list)
    tools_missing: list[str] = field(default_factory=list)


def run_cmd(cmd: list[str], cwd: str = ".") -> tuple[int, str, str]:
    """Run command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"


def has_tool(name: str) -> bool:
    """Check if a tool is available."""
    code, _, _ = run_cmd(["which", name])
    return code == 0


def detect_project_type(directory: str) -> ProjectType:
    """Detect the primary project type."""
    p = Path(directory)
    if (p / "go.mod").exists() or list(p.glob("**/*.go")):
        return ProjectType.GO
    if (p / "pyproject.toml").exists() or (p / "setup.py").exists():
        return ProjectType.PYTHON
    if (p / "tsconfig.json").exists():
        return ProjectType.TYPESCRIPT
    if (p / "package.json").exists():
        return ProjectType.JAVASCRIPT
    return ProjectType.UNKNOWN


def find_files(directory: str, pattern: str, exclude: list[str] = None) -> list[str]:
    """Find files matching pattern, excluding directories."""
    exclude = exclude or ["vendor", "node_modules", ".git", "__pycache__", "venv", ".venv"]
    
    if has_tool("fd"):
        cmd = ["fd", "-t", "f", pattern, directory]
        for ex in exclude:
            cmd.extend(["-E", ex])
        code, out, _ = run_cmd(cmd)
        if code == 0:
            return [f for f in out.strip().split("\n") if f]
    
    # Fallback to find
    cmd = ["find", directory, "-type", "f", "-name", pattern]
    for ex in exclude:
        cmd.extend(["!", "-path", f"*/{ex}/*"])
    code, out, _ = run_cmd(cmd)
    if code == 0:
        return [f for f in out.strip().split("\n") if f]
    return []


def grep_files(pattern: str, directory: str, glob: str = None, context_before: int = 0) -> list[tuple[str, int, str]]:
    """Search for pattern in files. Returns list of (file, line, content)."""
    results = []
    
    if has_tool("rg"):
        cmd = ["rg", "-n", "--no-heading"]
        if glob:
            cmd.extend(["-g", glob])
        if context_before:
            cmd.extend([f"-B{context_before}"])
        cmd.extend(["-e", pattern, directory])
        code, out, _ = run_cmd(cmd)
        if code == 0:
            for line in out.strip().split("\n"):
                if line and ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        try:
                            results.append((parts[0], int(parts[1]), parts[2]))
                        except ValueError:
                            pass
    return results


def count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except:
        return 0


# =============================================================================
# CHECK: Large Files
# =============================================================================

def check_size(directory: str, project_type: ProjectType) -> CheckResult:
    """Check for large files and high complexity."""
    result = CheckResult(name="size")
    findings = []
    
    # Determine file patterns based on project type
    patterns = {
        ProjectType.GO: ["*.go"],
        ProjectType.PYTHON: ["*.py"],
        ProjectType.JAVASCRIPT: ["*.js", "*.jsx"],
        ProjectType.TYPESCRIPT: ["*.ts", "*.tsx"],
        ProjectType.UNKNOWN: ["*.go", "*.py", "*.js", "*.ts"],
    }
    
    test_patterns = {
        ProjectType.GO: "_test.go",
        ProjectType.PYTHON: "test_",
        ProjectType.JAVASCRIPT: ".test.",
        ProjectType.TYPESCRIPT: ".test.",
    }
    
    file_sizes = []
    for pattern in patterns.get(project_type, patterns[ProjectType.UNKNOWN]):
        for filepath in find_files(directory, pattern):
            # Skip test files for size analysis
            test_pat = test_patterns.get(project_type, "")
            if test_pat and test_pat in filepath:
                continue
            
            lines = count_lines(filepath)
            if lines > 0:
                file_sizes.append((filepath, lines))
    
    # Sort by size descending
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    
    for filepath, lines in file_sizes[:20]:
        if lines > 800:
            findings.append(Finding(
                check="size",
                severity=Severity.CRITICAL.value,
                file=filepath,
                line=None,
                message=f"{lines} lines - very large file",
                action="Split into smaller modules"
            ))
        elif lines > 500:
            findings.append(Finding(
                check="size",
                severity=Severity.WARNING.value,
                file=filepath,
                line=None,
                message=f"{lines} lines - large file",
                action="Consider refactoring"
            ))
        elif lines > 300:
            findings.append(Finding(
                check="size",
                severity=Severity.INFO.value,
                file=filepath,
                line=None,
                message=f"{lines} lines",
                action="Monitor growth"
            ))
    
    # Note: For accurate function counting and complexity analysis, use:
    # - Go: go run scripts/gofuncs.go -dir <directory>
    # - Python: python scripts/pyfuncs.py --dir <directory>
    # - JS/TS: node scripts/jsfuncs.js --dir <directory>

    total_files = len(file_sizes)
    large_files = len([f for f in file_sizes if f[1] > 300])
    result.summary = f"Scanned {total_files} files, {large_files} exceed 300 lines"
    result.findings = findings[:15]  # Limit output
    return result


# =============================================================================
# CHECK: Test Coverage
# =============================================================================

def check_tests(directory: str, project_type: ProjectType) -> CheckResult:
    """Check for test coverage gaps."""
    result = CheckResult(name="tests")
    findings = []
    
    source_files = []
    test_files = []
    
    if project_type == ProjectType.GO:
        all_go = find_files(directory, "*.go")
        source_files = [f for f in all_go if not f.endswith("_test.go")]
        test_files = [f for f in all_go if f.endswith("_test.go")]
        
        # Check for coverage.out
        coverage_path = os.path.join(directory, "coverage.out")
        if os.path.exists(coverage_path):
            code, out, _ = run_cmd(["go", "tool", "cover", "-func", coverage_path], cwd=directory)
            if code == 0:
                # Parse lowest coverage functions
                lines = out.strip().split("\n")
                for line in lines[-25:]:
                    match = re.search(r"(\S+)\s+(\S+)\s+(\d+\.?\d*)%", line)
                    if match and float(match.group(3)) < 50:
                        findings.append(Finding(
                            check="tests",
                            severity=Severity.WARNING.value,
                            file=match.group(1),
                            line=None,
                            message=f"{match.group(2)}: {match.group(3)}% coverage",
                            action="Add test cases"
                        ))
        else:
            findings.append(Finding(
                check="tests",
                severity=Severity.INFO.value,
                file="",
                line=None,
                message="No coverage.out found",
                action="Run: go test ./... -coverprofile=coverage.out"
            ))
        
        # Find source files without corresponding test files
        # Note: For accurate exported function detection, use: go run scripts/gofuncs.go -dir <dir>
        for src in source_files:
            test_file = src.replace(".go", "_test.go")
            if test_file not in test_files and not src.endswith("_test.go"):
                # Only report if file has exported functions (basic regex check)
                matches = grep_files(r"^func [A-Z]", directory, glob=os.path.basename(src))
                if any(src in m[0] for m in matches):
                    findings.append(Finding(
                        check="tests",
                        severity=Severity.WARNING.value,
                        file=src,
                        line=None,
                        message="No test file for source with exported functions",
                        action=f"Create {os.path.basename(test_file)}"
                    ))
    
    elif project_type == ProjectType.PYTHON:
        all_py = find_files(directory, "*.py")
        source_files = [f for f in all_py if not ("test_" in f or "_test.py" in f or "/tests/" in f)]
        test_files = [f for f in all_py if "test_" in f or "_test.py" in f or "/tests/" in f]
    
    ratio = len(test_files) / max(len(source_files), 1) * 100
    result.summary = f"Source: {len(source_files)}, Tests: {len(test_files)}, Ratio: {ratio:.0f}%"
    result.findings = findings[:15]
    return result


# =============================================================================
# CHECK: Duplicates
# =============================================================================

def check_dupes(directory: str, project_type: ProjectType) -> CheckResult:
    """Check for duplicate code patterns."""
    result = CheckResult(name="dupes")
    findings = []
    
    # Note: For accurate duplicate function detection, use AST-based tools:
    # - Go: go run scripts/gofuncs.go -dir <directory>
    # - Python: python scripts/pyfuncs.py --dir <directory>
    # - JS/TS: node scripts/jsfuncs.js --dir <directory>
    # Then analyze output for duplicate names/signatures

    if project_type == ProjectType.GO:
        # Check for copy-paste hints
        hints = grep_files(r"(?i)(copy.?paste|same as|similar to|duplicate)", directory, glob="*.go")
        for filepath, line, content in hints[:5]:
            if "vendor/" not in filepath:
                findings.append(Finding(
                    check="dupes",
                    severity=Severity.INFO.value,
                    file=filepath,
                    line=line,
                    message="Copy-paste hint in comment",
                    action="Review for abstraction opportunity"
                ))
    
    result.summary = f"Found {len(findings)} potential duplicates"
    result.findings = findings[:15]
    return result


# =============================================================================
# CHECK: Dead Code
# =============================================================================

def check_dead(directory: str, project_type: ProjectType) -> CheckResult:
    """Check for dead/legacy code."""
    result = CheckResult(name="dead")
    findings = []
    
    # Legacy markers
    markers = grep_files(r"(TODO|FIXME|HACK|XXX|deprecated|legacy)", directory, glob="*.go" if project_type == ProjectType.GO else "*")
    for filepath, line, content in markers:
        if "vendor/" in filepath or "node_modules/" in filepath:
            continue
        
        severity = Severity.INFO.value
        if "FIXME" in content or "HACK" in content:
            severity = Severity.WARNING.value
        if "deprecated" in content.lower():
            severity = Severity.WARNING.value
        
        findings.append(Finding(
            check="dead",
            severity=severity,
            file=filepath,
            line=line,
            message=content.strip()[:80],
            action="Review and resolve or remove"
        ))
    
    if project_type == ProjectType.GO:
        # Unimplemented panics
        panics = grep_files(r'panic\("(unimplemented|not implemented|todo)"', directory, glob="*.go")
        for filepath, line, content in panics:
            if "vendor/" not in filepath:
                findings.append(Finding(
                    check="dead",
                    severity=Severity.CRITICAL.value,
                    file=filepath,
                    line=line,
                    message="Unimplemented code path",
                    action="Implement or remove"
                ))
        
        # Suggest static analysis
        if has_tool("staticcheck"):
            code, out, _ = run_cmd(["staticcheck", "./..."], cwd=directory)
            if out.strip():
                for line in out.strip().split("\n")[:10]:
                    match = re.match(r"([^:]+):(\d+):\d+: (.+)", line)
                    if match:
                        findings.append(Finding(
                            check="dead",
                            severity=Severity.WARNING.value,
                            file=match.group(1),
                            line=int(match.group(2)),
                            message=match.group(3)[:80],
                            action="Fix staticcheck issue"
                        ))
        else:
            findings.append(Finding(
                check="dead",
                severity=Severity.INFO.value,
                file="",
                line=None,
                message="staticcheck not installed",
                action="Install: go install honnef.co/go/tools/cmd/staticcheck@latest"
            ))
    
    result.summary = f"Found {len(findings)} legacy/dead code markers"
    result.findings = findings[:20]
    return result


# =============================================================================
# CHECK: Documentation
# =============================================================================

def check_docs(directory: str, project_type: ProjectType) -> CheckResult:
    """Check for documentation gaps."""
    result = CheckResult(name="docs")
    findings = []
    
    # Note: For comprehensive doc validation, use:
    # - Go: validate-docs.go (in llm-shared/utils/validate-docs)
    # - Functions: gofuncs.go, pyfuncs.py, jsfuncs.js for exported API analysis

    if project_type == ProjectType.GO:
        # Exported types without doc comments (basic regex check)
        type_matches = grep_files(r"^type [A-Z]", directory, glob="*.go", context_before=1)
        undoc_types = 0
        for filepath, line, content in type_matches:
            if "vendor/" in filepath:
                continue
            # Check if previous line is a comment
            # This is a heuristic - the grep with context would show it
            if not content.strip().startswith("//"):
                undoc_types += 1
                if undoc_types <= 10:
                    type_name = re.search(r"^type (\w+)", content)
                    if type_name:
                        findings.append(Finding(
                            check="docs",
                            severity=Severity.WARNING.value,
                            file=filepath,
                            line=line,
                            message=f"Exported type '{type_name.group(1)}' lacks doc comment",
                            action="Add // TypeName comment"
                        ))
        
        # Exported functions without doc comments
        func_matches = grep_files(r"^func [A-Z]", directory, glob="*.go", context_before=1)
        undoc_funcs = 0
        for filepath, line, content in func_matches:
            if "vendor/" in filepath or "_test.go" in filepath:
                continue
            if not content.strip().startswith("//"):
                undoc_funcs += 1
                if undoc_funcs <= 10:
                    func_name = re.search(r"^func (\w+)", content)
                    if func_name:
                        findings.append(Finding(
                            check="docs",
                            severity=Severity.WARNING.value,
                            file=filepath,
                            line=line,
                            message=f"Exported func '{func_name.group(1)}' lacks doc comment",
                            action="Add // FuncName comment"
                        ))
    
    # Check for README
    readme_path = os.path.join(directory, "README.md")
    if not os.path.exists(readme_path):
        findings.append(Finding(
            check="docs",
            severity=Severity.WARNING.value,
            file=directory,
            line=None,
            message="No README.md found",
            action="Create README with project overview"
        ))
    
    # Check for incomplete docs
    incomplete = grep_files(r"(TBD|TODO|WIP|FIXME)", directory, glob="*.md")
    for filepath, line, content in incomplete[:5]:
        findings.append(Finding(
            check="docs",
            severity=Severity.INFO.value,
            file=filepath,
            line=line,
            message="Incomplete documentation marker",
            action="Complete documentation"
        ))
    
    result.summary = f"Found {len(findings)} documentation issues"
    result.findings = findings[:15]
    return result


# =============================================================================
# Main
# =============================================================================

def print_report(report: HealthReport, json_output: bool = False):
    """Print the health report."""
    if json_output:
        output = {
            "directory": report.directory,
            "project_type": report.project_type,
            "tools_missing": report.tools_missing,
            "checks": []
        }
        for check in report.checks:
            output["checks"].append({
                "name": check.name,
                "summary": check.summary,
                "error": check.error,
                "findings": [f.to_dict() for f in check.findings]
            })
        print(json.dumps(output, indent=2))
        return
    
    severity_icons = {
        "critical": "🔴",
        "warning": "🟡",
        "info": "🟢"
    }
    
    print(f"\n{'='*60}")
    print(f"Code Health Report: {report.directory}")
    print(f"Project Type: {report.project_type}")
    print(f"{'='*60}\n")
    
    if report.tools_missing:
        print(f"⚠️  Missing tools: {', '.join(report.tools_missing)}")
        print("   Install for better results\n")
    
    for check in report.checks:
        print(f"## {check.name.upper()}")
        print(f"   {check.summary}")
        
        if check.error:
            print(f"   ❌ Error: {check.error}")
        
        if check.findings:
            print()
            for f in check.findings:
                icon = severity_icons.get(f.severity, "")
                loc = f"{f.file}"
                if f.line:
                    loc += f":{f.line}"
                print(f"   {icon} {loc}")
                print(f"      {f.message}")
                print(f"      → {f.action}")
                print()
        else:
            print("   ✅ No issues found\n")
        
        print()


def main():
    parser = argparse.ArgumentParser(description="Analyze codebase health")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to analyze")
    parser.add_argument("--check", choices=["size", "tests", "dupes", "dead", "docs"],
                        help="Run specific check only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    project_type = detect_project_type(directory)
    report = HealthReport(
        directory=directory,
        project_type=project_type.value
    )
    
    # Check for recommended tools
    for tool in ["rg", "fd", "git"]:
        if not has_tool(tool):
            report.tools_missing.append(tool)
    
    if project_type == ProjectType.GO:
        if not has_tool("staticcheck"):
            report.tools_missing.append("staticcheck")
    
    # Run checks
    checks = {
        "size": check_size,
        "tests": check_tests,
        "dupes": check_dupes,
        "dead": check_dead,
        "docs": check_docs,
    }
    
    if args.check:
        checks_to_run = [args.check]
    else:
        checks_to_run = list(checks.keys())
    
    for name in checks_to_run:
        try:
            result = checks[name](directory, project_type)
            report.checks.append(result)
        except Exception as e:
            report.checks.append(CheckResult(name=name, error=str(e)))
    
    print_report(report, json_output=args.json)


if __name__ == "__main__":
    main()
