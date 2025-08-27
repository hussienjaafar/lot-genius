from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).parent
PROMPTS = ROOT / "prompts"
DRAFTS = PROMPTS / "drafts"
APPROVED = PROMPTS / "approved"
REVIEWS = PROMPTS / "reviews"
ARCHIVE = PROMPTS / "archive"


def _ensure_dirs() -> None:
    for p in (PROMPTS, DRAFTS, APPROVED, REVIEWS, ARCHIVE):
        p.mkdir(parents=True, exist_ok=True)


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:60] or "prompt"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H-%M-%S")


def _write_prompt_file(folder: Path, pid: str, title: str, author: str, target: str, body: str) -> Path:
    name = f"{_now_iso()}_{pid}_{_slug(title)}.md"
    path = folder / name
    header = (
        f"---\n"
        f"id: {pid}\n"
        f"from: {author}\n"
        f"to: {target}\n"
        f"title: {title}\n"
        f"status: {'approved' if folder == APPROVED else 'draft'}\n"
        f"---\n\n"
    )
    path.write_text(header + body + "\n", encoding="utf-8")
    return path


def cmd_new(args):
    _ensure_dirs()
    pid = args.id or uuid.uuid4().hex
    title = args.title or "Untitled"
    author = args.from_agent
    target = args.to_agent
    if args.text:
        body = args.text
    elif args.file:
        body = Path(args.file).read_text(encoding="utf-8")
    else:
        print("Provide --text or --file", file=sys.stderr)
        raise SystemExit(2)
    p = _write_prompt_file(DRAFTS, pid, title, author, target, body)
    print(str(p))


def _iter_md(folder: Path):
    for p in sorted(folder.glob("*.md")):
        yield p


def cmd_list(args):
    _ensure_dirs()
    print("Drafts:")
    for p in _iter_md(DRAFTS):
        print(" -", p.name)
    if args.all:
        print("Approved:")
        for p in _iter_md(APPROVED):
            print(" -", p.name)


def _extract_id_from_path(p: Path) -> Optional[str]:
    m = re.search(r"_([0-9a-f]{32})_", p.name)
    if m:
        return m.group(1)
    # fallback to YAML header
    try:
        head = p.read_text(encoding="utf-8").splitlines()[:10]
        for line in head:
            if line.startswith("id:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def _find_prompt_by_id(pid: str, folder: Path) -> Optional[Path]:
    for p in folder.glob("*.md"):
        if pid in p.name:
            return p
        if _extract_id_from_path(p) == pid:
            return p
    return None


def _bus_send(text: str, meta: Optional[dict] = None, to: str = "claude", sender: str = "gemini") -> None:
    # Send a lightweight message referencing the prompt file
    cmd = [sys.executable, str(ROOT / "bus.py"), "send", "--from", sender, "--to", to, "--text", text]
    if meta is not None:
        cmd += ["--meta", json.dumps(meta)]
    subprocess.run(cmd, check=True)


def cmd_approve(args):
    _ensure_dirs()
    pid = args.id
    p = _find_prompt_by_id(pid, DRAFTS)
    if not p:
        print(f"Draft with id {pid} not found", file=sys.stderr)
        raise SystemExit(2)
    dest = APPROVED / p.name.replace("status: draft", "status: approved")
    # Move file
    p_final = APPROVED / p.name
    shutil.move(str(p), p_final)
    # Optional review note
    if args.note:
        note_path = REVIEWS / f"{_now_iso()}_{pid}_review.txt"
        note_path.write_text(args.note, encoding="utf-8")
    # Optionally send bus message pointing to this prompt file
    if args.send:
        rel = p_final.relative_to(Path.cwd()) if p_final.is_absolute() else p_final
        meta = {"prompt_id": pid, "path": str(rel), "title": args.title or p_final.name}
        _bus_send(text=f"APPROVED_PROMPT_FILE: {rel}", meta=meta, to=args.to_agent, sender=args.from_agent)
    print(str(p_final))


def cmd_send(args):
    # Send a bus message referencing an existing prompt file
    path = Path(args.path)
    if not path.exists():
        print(f"Path not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    rel = path.relative_to(Path.cwd()) if path.is_absolute() else path
    meta = {"prompt_id": _extract_id_from_path(path), "path": str(rel)}
    _bus_send(text=f"PROMPT_FILE: {rel}", meta=meta, to=args.to_agent, sender=args.from_agent)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prompt file workflow: drafts -> approved -> bus")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="Create a new draft prompt")
    p_new.add_argument("--title", required=False, default="Untitled")
    p_new.add_argument("--from", dest="from_agent", default="gpt5")
    p_new.add_argument("--to", dest="to_agent", default="claude")
    src = p_new.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="Prompt body text")
    src.add_argument("--file", help="Path to a file with prompt body")
    p_new.add_argument("--id", help="Optional custom prompt id")
    p_new.set_defaults(func=cmd_new)

    p_list = sub.add_parser("list", help="List draft prompts")
    p_list.add_argument("--all", action="store_true", help="Include approved")
    p_list.set_defaults(func=cmd_list)

    p_approve = sub.add_parser("approve", help="Approve a draft prompt and optionally send to Claude")
    p_approve.add_argument("--id", required=True, help="Prompt id")
    p_approve.add_argument("--note", default=None, help="Optional review note")
    p_approve.add_argument("--send", action="store_true", help="Send bus message referencing the approved file")
    p_approve.add_argument("--from", dest="from_agent", default="gemini")
    p_approve.add_argument("--to", dest="to_agent", default="claude")
    p_approve.add_argument("--title", default=None)
    p_approve.set_defaults(func=cmd_approve)

    p_send = sub.add_parser("send", help="Send a bus message referencing a prompt file")
    p_send.add_argument("--path", required=True)
    p_send.add_argument("--from", dest="from_agent", default="gemini")
    p_send.add_argument("--to", dest="to_agent", default="claude")
    p_send.set_defaults(func=cmd_send)

    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
