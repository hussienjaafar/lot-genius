from __future__ import annotations

import argparse
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).parent
PROMPTS = ROOT / "prompts"


def _latest(folder: Path) -> Path | None:
    files = sorted(folder.glob("*.md"))
    return files[-1] if files else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Send latest approved (default) or draft prompt to Claude via bus")
    parser.add_argument("--approved", action="store_true", help="Use latest approved (default)")
    parser.add_argument("--draft", dest="approved", action="store_false", help="Use latest draft instead")
    parser.set_defaults(approved=True)
    parser.add_argument("--from", dest="from_agent", default="gemini")
    parser.add_argument("--to", dest="to_agent", default="claude")
    args = parser.parse_args(argv)

    folder = (PROMPTS / "approved") if args.approved else (PROMPTS / "drafts")
    p = _latest(folder)
    if not p:
        print(f"No {'approved' if args.approved else 'draft'} prompts found", file=sys.stderr)
        return 1

    rel = p if not p.is_absolute() else p.relative_to(Path.cwd())
    text = f"PROMPT_FILE: {rel}"
    meta = {"prompt_path": str(rel)}
    cmd = [
        sys.executable,
        str(ROOT / "bus.py"),
        "send",
        "--from",
        args.from_agent,
        "--to",
        args.to_agent,
        "--text",
        text,
        "--meta",
        __import__("json").dumps(meta),
    ]
    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
