#!/usr/bin/env python3
"""
Release notes generator for Lot Genius.
Reads Gap Fix run logs and synthesizes a compact changelog.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def sanitize_text(text: str) -> str:
    """Remove or replace non-ASCII characters with ASCII equivalents."""
    # Common Unicode replacements
    replacements = {
        '\u2705': '[OK]',        # ✅ checkmark
        '\u274C': '[FAIL]',      # ❌ cross mark
        '\u2192': '->',          # → arrow
        '\u2190': '<-',          # ← arrow
        '\u2191': '^',           # ↑ arrow
        '\u2193': 'v',           # ↓ arrow
        '\u2265': '>=',          # ≥ greater or equal
        '\u2264': '<=',          # ≤ less or equal
        '\u2260': '!=',          # ≠ not equal
        '\u03B1': 'alpha',      # α
        '\u03B2': 'beta',       # β
        '\u03B3': 'gamma',      # γ
        '\u03B4': 'delta',      # δ
        '\u03B5': 'epsilon',    # ε
        '\u03BB': 'lambda',     # λ
        '\u03BC': 'mu',         # μ
        '\u03C3': 'sigma',      # σ
        '\u0394': 'Delta',      # Δ
        '\u2014': '--',         # em dash
        '\u2013': '-',          # en dash
        '\u2011': '-',          # non-breaking hyphen
        '\u00D7': 'x',          # × multiplication
        '\u251C': '|-',         # ├ box drawing
        '\u2500': '-',          # ─ box drawing
        '\u2514': '`-',         # └ box drawing
    }

    result = text
    for unicode_char, ascii_replacement in replacements.items():
        result = result.replace(unicode_char, ascii_replacement)

    # Remove any remaining non-ASCII characters
    result = ''.join(char if ord(char) < 128 else '?' for char in result)

    return result


def extract_gap_fix_info(file_path: Path) -> Tuple[str, str, str]:
    """Extract title, objective, and key changes from a Gap Fix run log."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Sanitize content to ASCII
        content = sanitize_text(content)

        # Extract title (first # heading)
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        # Extract objective (first **Objective**: line)
        objective_match = re.search(r'\*\*Objective\*\*:\s*(.+?)(?:\n|$)', content)
        objective = objective_match.group(1) if objective_match else ""

        # Extract implementation summary or key points (look for ## Implementation Summary or ## Summary)
        summary_match = re.search(
            r'## (?:Implementation )?Summary\n\n(.+?)(?:\n## |\n### |$)',
            content,
            re.DOTALL
        )

        if summary_match:
            summary_text = summary_match.group(1).strip()
            # Extract first few bullet points or first paragraph
            lines = summary_text.split('\n')
            key_points = []
            for line in lines[:5]:  # First 5 lines
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    key_points.append(line[2:])
                elif line and not line.startswith('#'):
                    # Take first sentence of paragraph
                    sentences = line.split('. ')
                    if sentences:
                        key_points.append(sentences[0] + ('.' if not sentences[0].endswith('.') else ''))
                        break
            summary = ' '.join(key_points)[:200]  # Limit length
        else:
            summary = ""

        return title, objective, summary

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return file_path.stem, "", ""


def generate_release_notes() -> str:
    """Generate release notes from Gap Fix run logs."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    runlogs_dir = repo_root / "multi_agent" / "runlogs"

    if not runlogs_dir.exists():
        return "# Release Notes\n\nNo run logs found for release notes generation.\n"

    # Find all gapfix_*.md files
    gap_fix_files = sorted(runlogs_dir.glob("gapfix_*.md"))

    if not gap_fix_files:
        return "# Release Notes\n\nNo Gap Fix run logs found.\n"

    # Extract version from git tag if available
    version = "v0.1.0"  # Default version
    try:
        import subprocess
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        if result.returncode == 0:
            version = result.stdout.strip()
    except Exception:
        pass

    # Group changes by category
    categories = {
        "Backend Infrastructure": [],
        "Frontend & UI": [],
        "Documentation & Quality": [],
        "Development & CI": [],
        "Bug Fixes & Polish": []
    }

    category_keywords = {
        "Backend Infrastructure": ["backend", "api", "pipeline", "database", "cache", "keepa"],
        "Frontend & UI": ["frontend", "ui", "ux", "react", "nextjs", "streaming", "sse"],
        "Documentation & Quality": ["docs", "unicode", "ascii", "encoding", "validation"],
        "Development & CI": ["ci", "test", "e2e", "quality", "gate", "workflow"],
        "Bug Fixes & Polish": ["fix", "polish", "resilience", "error", "cleanup"]
    }

    # Process each Gap Fix
    for gap_file in gap_fix_files:
        title, objective, summary = extract_gap_fix_info(gap_file)

        # Determine category based on keywords
        file_content = title.lower() + " " + objective.lower() + " " + summary.lower()
        best_category = "Bug Fixes & Polish"  # default
        best_score = 0

        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in file_content)
            if score > best_score:
                best_score = score
                best_category = category

        # Format entry
        gap_number = re.search(r'gapfix_(\d+)', gap_file.stem)
        gap_num = gap_number.group(1) if gap_number else "?"

        # Clean title to remove "Gap Fix N: " prefix
        clean_title = re.sub(r'^Gap Fix \d+:\s*', '', title)

        entry = f"**{clean_title}** (Gap Fix {gap_num})"
        if objective:
            entry += f": {objective}"
        entry += f" [[{gap_file.name}](multi_agent/runlogs/{gap_file.name})]"

        categories[best_category].append(entry)

    # Generate release notes
    notes = [
        f"# Release Notes - {version}",
        "",
        f"This release includes {len(gap_fix_files)} Gap Fix implementations that enhance the Lot Genius platform with improved functionality, reliability, and developer experience.",
        "",
        "## What's New",
        ""
    ]

    # Add non-empty categories
    for category, items in categories.items():
        if items:
            notes.append(f"### {category}")
            notes.append("")
            for item in items:
                notes.append(f"- {item}")
            notes.append("")

    # Add artifacts section
    notes.extend([
        "## Release Artifacts",
        "",
        "This release includes the following downloadable artifacts:",
        "",
        "- **Backend Packages**: Python wheel and source distribution for lotgenius package",
        "- **Frontend Build**: Production-ready Next.js application bundle",
        "- **Documentation Bundle**: Complete offline documentation with validation scripts",
        "",
        "## Installation & Usage",
        "",
        "**Backend Package**:",
        "```bash",
        "pip install lotgenius-0.1.0-py3-none-any.whl",
        "```",
        "",
        "**Frontend Deployment**:",
        "```bash",
        "unzip frontend-build.zip",
        "npm start  # or deploy .next/ directory to your hosting platform",
        "```",
        "",
        "**Documentation**:",
        "```bash",
        "unzip docs-bundle.zip",
        "# Browse docs/ directory or run validation scripts",
        "python scripts/check_ascii.py docs/",
        "```",
        "",
        "## System Requirements",
        "",
        "- **Backend**: Python 3.11+ with dependencies listed in requirements",
        "- **Frontend**: Node.js 18+ for development, static files for deployment",
        "- **Documentation**: Python 3.11+ for validation scripts (optional)",
        "",
        f"For detailed implementation notes, see the complete run logs in [multi_agent/runlogs/](multi_agent/runlogs/).",
        ""
    ])

    return '\n'.join(notes)


def main():
    """Generate and print release notes."""
    notes = generate_release_notes()
    print(notes)


if __name__ == "__main__":
    main()
