"""Shared HTTP client for Gitee `/v1/messages` (Qwen chat, non-streaming)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


def load_aigc_dotenv() -> None:
    """Load `.env` from aigc root, workspace root, or cwd (merge; skip keys already set)."""
    this = Path(__file__).resolve().parent
    candidates = (
        this.parent.parent / ".env",  # …/aigc/.env
        this.parent.parent.parent / ".env",  # workspace root
        Path.cwd() / ".env",
    )
    for env_path in candidates:
        env_path = env_path.resolve()
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k and k not in os.environ:
                os.environ[k] = v.strip().strip('"').strip("'")


def extract_assistant_text(body: dict[str, Any]) -> str:
    def _flatten_content_blocks(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if isinstance(block.get("text"), str):
                    chunks.append(block["text"])
                elif isinstance(block.get("content"), str):
                    chunks.append(block["content"])
            return "".join(chunks)
        return ""

    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict):
                t = _flatten_content_blocks(msg.get("content"))
                if t:
                    return t
            text = first.get("text")
            if isinstance(text, str):
                return text

    if body.get("type") == "message" or body.get("role") == "assistant":
        t = _flatten_content_blocks(body.get("content"))
        if t:
            return t

    return ""


def post_messages(
    api_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: int = 180,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(
        api_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        code = e.code
        if code >= 500:
            raise RuntimeError(f"HTTP {code} server error (retryable)\n{err_body[:2000]}") from e
        if code == 429:
            raise RuntimeError(f"HTTP {code} rate limited (retryable)\n{err_body[:2000]}") from e
        raise SystemExit(f"HTTP {code} {e.reason} (not retryable)\n{err_body[:2000]}") from e
    except URLError as e:
        raise RuntimeError(f"Network error (retryable): {e}") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        raise SystemExit(f"Invalid JSON response: {raw[:500]}") from err
