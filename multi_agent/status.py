from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent
PROMPTS = ROOT / "prompts"


def _read_jsonl(path: Path):
    try:
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except Exception:
        return []


def main() -> int:
    drafts = sorted((PROMPTS / "drafts").glob("*.md"))
    approved = sorted((PROMPTS / "approved").glob("*.md"))
    print("Prompts:")
    print(f" - drafts:   {len(drafts)}" + (f" (latest: {drafts[-1].name})" if drafts else ""))
    print(f" - approved: {len(approved)}" + (f" (latest: {approved[-1].name})" if approved else ""))

    msgs = _read_jsonl(ROOT / "messages.jsonl")
    reps = _read_jsonl(ROOT / "replies.jsonl")
    events = (msgs + reps)[-5:]
    if events:
        print("Bus (last 5 events):")
        for ev in events:
            who = ev.get("from") or ev.get("agent")
            txt = ev.get("text") or f"ack:{ev.get('msg_id')}"
            print(f" - {who}: {txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
