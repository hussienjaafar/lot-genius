from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic


ROOT = Path(__file__).parent


def call_claude_api(prompt_content: str) -> str:
    """Calls the Claude API to implement the code."""
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt_content,
                }
            ],
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}", file=sys.stderr)
        return f"Error: {e}"  # Return error message on failure


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Claude Implementer")
    parser.add_argument("--agent", default="claude", help="The agent name for the bus")
    args = parser.parse_args(argv)

    # 1. Fetch the next message from the bus
    next_message_cmd = [
        sys.executable,
        str(ROOT / "bus.py"),
        "next",
        "--agent",
        args.agent,
    ]
    result = subprocess.run(next_message_cmd, capture_output=True, text=True, check=True)
    message_json = result.stdout.strip()

    if not message_json:
        print("No pending messages for Claude.")
        return 0

    message = json.loads(message_json)
    prompt_id = message.get("meta", {}).get("prompt_id")
    prompt_path = message.get("meta", {}).get("path")

    if not prompt_id or not prompt_path:
        print("Error: Message does not contain prompt information.", file=sys.stderr)
        return 1

    # 2. Implement the code
    print(f"--- Implementing Prompt ID: {prompt_id} ---")
    prompt_content = (ROOT / Path(prompt_path)).read_text(encoding="utf-8")
    implemented_code = call_local_claude_api(prompt_content)
    print("--- End of Implementation ---")

    # 3. Send a reply to the orchestrator (GPT-5)
    reply_text = f"Implementation for prompt {prompt_id}:\n\n{implemented_code}"
    reply_cmd = [
        sys.executable,
        str(ROOT / "bus.py"),
        "reply",
        "--from",
        "claude",
        "--to",
        "gpt5",
        "--parent",
        message["id"],
        "--text",
        reply_text,
    ]
    subprocess.run(reply_cmd, check=True)

    print(f"Replied to GPT-5 for prompt {prompt_id}.")

    # 4. Acknowledge the message
    ack_message_cmd = [
        sys.executable,
        str(ROOT / "bus.py"),
        "ack",
        "--msg-id",
        message["id"],
        "--agent",
        args.agent,
    ]
    subprocess.run(ack_message_cmd, check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
