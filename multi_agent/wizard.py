from __future__ import annotations

import uuid
from pathlib import Path
import time
import re

ROOT = Path(__file__).parent
DRAFTS = ROOT / "prompts" / "drafts"


def _ensure():
    DRAFTS.mkdir(parents=True, exist_ok=True)


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:60] or "prompt"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H-%M-%S")


def main() -> int:
    _ensure()
    print("Create a new draft prompt (wizard). Press Enter to skip a section.")
    title = input("Title: ").strip() or "Untitled"
    frm = input("From (default gpt5): ").strip() or "gpt5"
    to = input("To (default claude): ").strip() or "claude"
    sections = []
    ctx = input("Context (what/why): ")
    if ctx:
        sections.append("## Context\n\n" + ctx.strip())
    chg = input("Changes (what to implement): ")
    if chg:
        sections.append("## Changes\n\n" + chg.strip())
    acc = input("Acceptance Criteria (bullet points): ")
    if acc:
        sections.append("## Acceptance Criteria\n\n" + acc.strip())
    tst = input("Test Plan (steps): ")
    if tst:
        sections.append("## Tests\n\n" + tst.strip())
    body = ("\n\n".join(sections) or "(fill in details)") + "\n"
    pid = uuid.uuid4().hex
    name = f"{_now()}_{pid}_{_slug(title)}.md"
    path = DRAFTS / name
    header = (
        f"---\n"
        f"id: {pid}\n"
        f"from: {frm}\n"
        f"to: {to}\n"
        f"title: {title}\n"
        f"status: draft\n"
        f"---\n\n"
    )
    path.write_text(header + body, encoding="utf-8")
    print(f"Draft created: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
