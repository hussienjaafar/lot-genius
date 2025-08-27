from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


BASE = Path(__file__).parent
MSG = BASE / "messages.jsonl"
REP = BASE / "replies.jsonl"
ACK = BASE / "acks.jsonl"
AGENTS = BASE / "agents.json"


def _ensure_files() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    for p in (MSG, REP, ACK):
        if not p.exists():
            p.write_text("", encoding="utf-8")


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                # Skip malformed lines
                continue
    return out


def _append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load_agents() -> Dict[str, dict]:
    if AGENTS.exists():
        try:
            return json.loads(AGENTS.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_agents(d: Dict[str, dict]) -> None:
    AGENTS.write_text(json.dumps(d, indent=2), encoding="utf-8")


def cmd_init(args):
    _ensure_files()
    if not AGENTS.exists():
        _save_agents(
            {
                "codex": {"role": "orchestrator", "description": "Codex CLI"},
                "claude": {"role": "assistant", "description": "Claude CLI"},
                "gemini": {"role": "assistant", "description": "Gemini CLI"},
            }
        )
    print(str(BASE))


def _normalize_to(to: Optional[str | List[str]]) -> List[str] | str:
    if to is None:
        return "all"
    if isinstance(to, str):
        if to.lower() in ("all", "*"):
            return "all"
        return [to]
    return to


def cmd_send(args):
    _ensure_files()
    msg = {
        "id": args.id or uuid.uuid4().hex,
        "ts": time.time(),
        "from": args.from_agent,
        "to": _normalize_to(args.to),
        "text": args.text,
        "meta": json.loads(args.meta) if args.meta else None,
    }
    _append_jsonl(MSG, msg)
    print(msg["id"])  # print ID for piping


def cmd_reply(args):
    _ensure_files()
    rep = {
        "id": args.id or uuid.uuid4().hex,
        "parent_id": args.parent,
        "ts": time.time(),
        "from": args.from_agent,
        "to": _normalize_to(args.to),
        "text": args.text,
        "meta": json.loads(args.meta) if args.meta else None,
    }
    _append_jsonl(REP, rep)
    print(rep["id"])  # print new reply ID


def cmd_ack(args):
    _ensure_files()
    rec = {"msg_id": args.msg_id, "agent": args.agent, "ts": time.time()}
    _append_jsonl(ACK, rec)


def _is_addressed_to(record_to: Any, agent: str) -> bool:
    if record_to == "all" or record_to == "*" or record_to is None:
        return True
    if isinstance(record_to, list):
        return agent in record_to
    if isinstance(record_to, str):
        return agent == record_to
    return False


def _index_by_parent(replies: List[dict]) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}
    for r in replies:
        pid = r.get("parent_id")
        if not pid:
            continue
        out.setdefault(pid, []).append(r)
    return out


def cmd_next(args):
    _ensure_files()
    agent = args.agent
    msgs = _read_jsonl(MSG)
    replies = _read_jsonl(REP)
    acks = _read_jsonl(ACK)
    seen_pairs = {(a.get("msg_id"), a.get("agent")) for a in acks}
    replies_by_parent = _index_by_parent(replies)

    for m in msgs:
        if m.get("from") == agent:
            continue
        if not _is_addressed_to(m.get("to"), agent):
            continue
        if (m.get("id"), agent) in seen_pairs:
            continue
        # already replied by this agent?
        if any(r.get("from") == agent for r in replies_by_parent.get(m.get("id"), [])):
            continue
        print(json.dumps(m, ensure_ascii=False))
        return
    # nothing pending
    print("")


def _fmt_row(kind: str, d: dict) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(d.get("ts", time.time())))
    who = d.get("from") or d.get("agent") or "?"
    text = d.get("text") or ""
    if kind == "msg":
        to = d.get("to")
        return f"[{ts}] {who} -> {to}: {text} (id={d.get('id')})"
    if kind == "rep":
        to = d.get("to")
        return f"[{ts}] {who} -> {to}: {text} (reply to={d.get('parent_id')})"
    if kind == "ack":
        return f"[{ts}] ack by {who} for {d.get('msg_id')}"
    return json.dumps(d)


def cmd_tail(args):
    _ensure_files()
    # one-shot print (sorted by ts) unless --follow
    def dump_once():
        rows: List[tuple[float, str]] = []
        for d in _read_jsonl(MSG):
            rows.append((float(d.get("ts", 0.0)), _fmt_row("msg", d)))
        for d in _read_jsonl(REP):
            rows.append((float(d.get("ts", 0.0)), _fmt_row("rep", d)))
        if args.with_acks:
            for d in _read_jsonl(ACK):
                rows.append((float(d.get("ts", 0.0)), _fmt_row("ack", d)))
        for _, line in sorted(rows, key=lambda x: x[0]):
            print(line)

    dump_once()
    if not args.follow:
        return

    # Follow: poll the files for growth
    last_sizes = {MSG: MSG.stat().st_size if MSG.exists() else 0,
                  REP: REP.stat().st_size if REP.exists() else 0,
                  ACK: ACK.stat().st_size if ACK.exists() else 0}
    seen_ids: set[str] = set()
    for d in _read_jsonl(MSG):
        if d.get("id"):
            seen_ids.add(d["id"])
    for d in _read_jsonl(REP):
        if d.get("id"):
            seen_ids.add(d["id"])

    try:
        while True:
            time.sleep(max(0.2, float(args.interval)))
            resized = False
            for p in (MSG, REP, ACK):
                try:
                    sz = p.stat().st_size
                except FileNotFoundError:
                    sz = 0
                if sz != last_sizes[p]:
                    last_sizes[p] = sz
                    resized = True
            if not resized:
                continue
            # print only new records
            for d in _read_jsonl(MSG):
                i = d.get("id")
                if i and i not in seen_ids:
                    print(_fmt_row("msg", d))
                    seen_ids.add(i)
            for d in _read_jsonl(REP):
                i = d.get("id")
                if i and i not in seen_ids:
                    print(_fmt_row("rep", d))
                    seen_ids.add(i)
            if args.with_acks:
                for d in _read_jsonl(ACK):
                    # acks may not have IDs; print all new chronologically in dump_once only
                    pass
    except KeyboardInterrupt:
        return


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="File-based multi-agent bus")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize bus and default agents")
    p_init.set_defaults(func=cmd_init)

    p_send = sub.add_parser("send", help="Send a message")
    p_send.add_argument("--from", dest="from_agent", required=True)
    p_send.add_argument("--to", dest="to", default="all")
    p_send.add_argument("--text", required=True)
    p_send.add_argument("--meta", default=None, help="JSON string for meta")
    p_send.add_argument("--id", default=None, help="Optional custom message id")
    p_send.set_defaults(func=cmd_send)

    p_next = sub.add_parser("next", help="Fetch next pending message for an agent")
    p_next.add_argument("--agent", required=True)
    p_next.set_defaults(func=cmd_next)

    p_reply = sub.add_parser("reply", help="Reply to a message")
    p_reply.add_argument("--from", dest="from_agent", required=True)
    p_reply.add_argument("--parent", required=True, help="Parent message id")
    p_reply.add_argument("--to", dest="to", default="all")
    p_reply.add_argument("--text", required=True)
    p_reply.add_argument("--meta", default=None)
    p_reply.add_argument("--id", default=None)
    p_reply.set_defaults(func=cmd_reply)

    p_ack = sub.add_parser("ack", help="Acknowledge a message for an agent")
    p_ack.add_argument("--msg-id", required=True)
    p_ack.add_argument("--agent", required=True)
    p_ack.set_defaults(func=cmd_ack)

    p_tail = sub.add_parser("tail", help="Tail conversation (messages + replies)")
    p_tail.add_argument("--follow", action="store_true")
    p_tail.add_argument("--interval", default=0.5)
    p_tail.add_argument("--with-acks", action="store_true")
    p_tail.set_defaults(func=cmd_tail)

    args = parser.parse_args(list(argv) if argv is not None else None)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
