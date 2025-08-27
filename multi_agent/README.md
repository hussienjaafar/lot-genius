Multi‑Agent File Bus

Lightweight, file‑based message bus so three CLIs — this assistant (Codex CLI), Claude CLI, and Gemini CLI — can interact locally without network services.

How it works

- Messages are append‑only JSONL files under this folder.
- Each agent writes messages to `messages.jsonl` and optional replies to `replies.jsonl`.
- Acks ("I saw this") go to `acks.jsonl` to avoid duplicate handling.
- The `bus.py` helper provides simple commands: `init`, `send`, `next`, `reply`, `ack`, and `tail`.

Files

- `messages.jsonl`: one JSON per line: { id, ts, from, to, text, meta }
- `replies.jsonl`: replies linked to a parent: { id, parent_id, ts, from, to, text, meta }
- `acks.jsonl`: acknowledgements: { msg_id, agent, ts }
- `agents.json`: optional registry of known agents and roles

Quick start

1. Initialize the bus with default agents

   python multi_agent/bus.py init

2. Send a message to everyone (broadcast)

   python multi_agent/bus.py send --from codex --to all --text "Hello Claude and Gemini!"

3. Let Claude fetch the next pending message addressed to it

   python multi_agent/bus.py next --agent claude

4. Claude replies (using the `id` printed in step 3 as PARENT)

   python multi_agent/bus.py reply --from claude --parent PARENT --text "Got it. Here's my reply."

5. Tail the conversation (messages + replies)

   python multi_agent/bus.py tail

Windows wrapper scripts

- Convenience .bat files are provided in `multi_agent/wrappers/` for Claude and Gemini.

Claude (Windows CMD):

- `multi_agent\wrappers\claude-send.bat --to all --text "Hello"`
- `multi_agent\wrappers\claude-next.bat`
- `multi_agent\wrappers\claude-reply.bat --parent <MSG_ID> --text "Replying"`
- `multi_agent\wrappers\claude-ack.bat --msg-id <MSG_ID>`

Gemini (Windows CMD):

- `multi_agent\wrappers\gemini-send.bat --to claude --text "Hi Claude"`
- `multi_agent\wrappers\gemini-next.bat`
- `multi_agent\wrappers\gemini-reply.bat --parent <MSG_ID> --text "Replying"`
- `multi_agent\wrappers\gemini-ack.bat --msg-id <MSG_ID>`

Notes:

- All other flags from `bus.py` are supported and passed through.
- Ensure `python` is available on PATH; otherwise edit the .bat files to point to your Python.

POSIX wrapper scripts (Linux/macOS/WSL)

- Located in `multi_agent/wrappers/` with `.sh` extensions; make them executable: `chmod +x multi_agent/wrappers/*.sh`.

Claude (POSIX):

- `multi_agent/wrappers/claude-send.sh --to all --text "Hello"`
- `multi_agent/wrappers/claude-next.sh`
- `multi_agent/wrappers/claude-reply.sh --parent <MSG_ID> --text "Replying"`
- `multi_agent/wrappers/claude-ack.sh --msg-id <MSG_ID>`

Gemini (POSIX):

- `multi_agent/wrappers/gemini-send.sh --to claude --text "Hi Claude"`
- `multi_agent/wrappers/gemini-next.sh`
- `multi_agent/wrappers/gemini-reply.sh --parent <MSG_ID> --text "Replying"`
- `multi_agent/wrappers/gemini-ack.sh --msg-id <MSG_ID>`

Notes:

- Wrappers auto-detect `python` or `python3` on PATH.

Agent naming

- Use these canonical names unless you customize `agents.json`:
  - codex (this assistant)
  - claude (Claude CLI)
  - gemini (Gemini CLI)

Integrating external CLIs

- Claude CLI / Gemini CLI can call the same commands (send/next/reply) to participate.
- If they cannot run Python, they can append raw JSON lines to the files using their shell.

JSON schemas (concise)

- Message: { "id": str, "ts": float, "from": str, "to": [str]|"all", "text": str, "meta": object|null }
- Reply: { "id": str, "parent_id": str, "ts": float, "from": str, "to": [str]|"all", "text": str, "meta": object|null }
- Ack: { "msg_id": str, "agent": str, "ts": float }

Notes

- Files are append‑only to be concurrency‑friendly.
- `next` does not modify history; use `ack` or `reply` to mark progress.
- You can run multiple terminals for each agent, all pointing to this folder.
