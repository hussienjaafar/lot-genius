from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GPT-5 Orchestrator")
    parser.add_argument("--task", required=True, help="Task description for the new prompt")
    args = parser.parse_args(argv)

    # 1. Create a new draft prompt
    prompt_title = f"Task: {args.task[:50]}"
    prompt_body = f"""
## Task

{args.task}

## Plan

(GPT-5 to fill in the plan)

## Prompt for Claude

(GPT-5 to generate the prompt for Claude)
"""
    new_prompt_cmd = [
        sys.executable,
        str(ROOT / "prompt_flow.py"),
        "new",
        "--title",
        prompt_title,
        "--from",
        "gpt5",
        "--to",
        "claude",
        "--text",
        prompt_body,
    ]
    result = subprocess.run(new_prompt_cmd, capture_output=True, text=True, check=True)
    prompt_path = result.stdout.strip()
    prompt_id_match = [line for line in (ROOT / prompt_path).read_text().splitlines() if line.startswith("id:")]
    prompt_id = prompt_id_match[0].split(":")[1].strip() if prompt_id_match else None

    if not prompt_id:
        print("Error: Could not extract prompt ID from the created file.", file=sys.stderr)
        return 1

    # 2. Send a message to Gemini for review
    message_text = f"New prompt draft for review: {prompt_title}"
    meta = {"prompt_id": prompt_id, "path": prompt_path}
    send_message_cmd = [
        sys.executable,
        str(ROOT / "bus.py"),
        "send",
        "--from",
        "gpt5",
        "--to",
        "gemini",
        "--text",
        message_text,
        "--meta",
        json.dumps(meta),
    ]
    subprocess.run(send_message_cmd, check=True)

    print(f"Draft prompt created: {prompt_path}")
    print(f"Message sent to Gemini for review. Prompt ID: {prompt_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
