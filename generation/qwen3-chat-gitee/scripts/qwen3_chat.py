#!/usr/bin/env python3
"""Call Gitee Serverless Qwen3 chat API (POST /v1/messages), non-streaming JSON.

Environment:
  AIGC_GITEE_API_KEY   required
  AIGC_GITEE_BASE_URL  optional, default https://ai.gitee.com/v1
  AIGC_QWEN3_MODEL     optional, default Qwen3-32B

Usage:
  python qwen3_chat.py --prompt "你好"
  python qwen3_chat.py --request path/to/body.json
  python qwen3_chat.py --prompt "Hi" --plain
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

from client import (
    extract_assistant_text,
    load_aigc_dotenv,
    post_messages,
)


def default_payload(model: str, user_prompt: str) -> dict[str, Any]:
    return {
        "model": model,
        "stream": False,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "messages": [{"role": "user", "content": user_prompt}],
    }


def main() -> None:
    load_aigc_dotenv()
    # Same token as MV video scripts (generate_video_assets.py)
    if not os.getenv("AIGC_GITEE_API_KEY") and os.getenv("GITEE_API_TOKEN"):
        os.environ["AIGC_GITEE_API_KEY"] = os.getenv("GITEE_API_TOKEN", "")

    import config as qwen_cfg  # after dotenv / alias

    parser = argparse.ArgumentParser(description="Gitee Qwen3 chat (non-streaming)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", "-p", help="Single user message")
    group.add_argument(
        "--request", "-r", type=Path, help="JSON request body file"
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Print only assistant text to stdout",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON body only, do not POST",
    )
    args = parser.parse_args()

    if args.request:
        payload = json.loads(Path(args.request).resolve().read_text(encoding="utf-8"))
    else:
        payload = default_payload(qwen_cfg.DEFAULT_MODEL, args.prompt or "")

    if "model" not in payload or not payload["model"]:
        payload["model"] = qwen_cfg.DEFAULT_MODEL
    if payload.get("stream") is True:
        raise SystemExit("Only non-stream mode: set \"stream\": false in the request.")
    payload["stream"] = False

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if not qwen_cfg.API_KEY:
        raise SystemExit(
            "Missing AIGC_GITEE_API_KEY. Set it in the environment or aigc/.env"
        )

    response = post_messages(
        qwen_cfg.API_URL, qwen_cfg.API_KEY, payload, timeout=120
    )

    if args.plain:
        print(extract_assistant_text(response).strip())
    else:
        out = {
            "assistant_text": extract_assistant_text(response),
            "usage": response.get("usage"),
            "model": response.get("model"),
            "id": response.get("id"),
            "raw": response,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
