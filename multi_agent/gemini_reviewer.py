from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import google.generativeai as genai


ROOT = Path(__file__).parent


def call_gemini_api(prompt_content: str) -> str:
    """Calls the Gemini API to review the prompt content."""
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt_content)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return prompt_content  # Return original content on error


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Gemini Reviewer")
    parser.add_argument("--agent", default="gemini", help="The agent name for the bus")
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
        print("No pending messages for Gemini.")
        return 0

    message = json.loads(message_json)
    prompt_id = message.get("meta", {}).get("prompt_id")
    prompt_path = message.get("meta", {}).get("path")

    if not prompt_id or not prompt_path:
        print("Error: Message does not contain prompt information.", file=sys.stderr)
        return 1

    # 2. Review the prompt
    print(f"--- Reviewing Prompt ID: {prompt_id} ---")
    prompt_content = (ROOT / prompt_path).read_text(encoding="utf-8")
    reviewed_content = call_local_gemini_api(prompt_content)
    (ROOT / prompt_path).write_text(reviewed_content, encoding="utf-8")
    print("--- End of Review ---")

    # 3. Approve the prompt and send to Claude
    approve_prompt_cmd = [
        sys.executable,
        str(ROOT / "prompt_flow.py"),
        "approve",
        "--id",
        prompt_id,
        "--send",
        "--from",
        "gemini",
        "--to",
        "claude",
        "--note",
        "Approved by Gemini.",
    ]
    subprocess.run(approve_prompt_cmd, check=True)

    print(f"Prompt {prompt_id} approved and sent to Claude.")

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
