from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DRAFTS = ROOT / "prompts" / "drafts"


def _latest() -> Path | None:
    files = sorted(DRAFTS.glob("*.md"))
    return files[-1] if files else None


def _extract_id_from_name(name: str) -> str | None:
    m = re.search(r"_([0-9a-f]{32})_", name)
    return m.group(1) if m else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Approve latest draft and optionally send to Claude")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--from", dest="from_agent", default="gemini")
    parser.add_argument("--to", dest="to_agent", default="claude")
    parser.add_argument("--note", default=None)
    parser.add_argument("--title", default=None)
    args = parser.parse_args(argv)

    p = _latest()
    if not p:
        print("No draft prompts found", file=sys.stderr)
        return 1
    pid = _extract_id_from_name(p.name)
    if not pid:
        print(f"Cannot extract id from {p.name}", file=sys.stderr)
        return 1

    cmd = [
        sys.executable,
        str(ROOT / "prompt_flow.py"),
        "approve",
        "--id",
        pid,
        "--from",
        args.from_agent,
        "--to",
        args.to_agent,
    ]
    if args.send:
        cmd.append("--send")
    if args.note:
        cmd += ["--note", args.note]
    if args.title:
        cmd += ["--title", args.title]

    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
