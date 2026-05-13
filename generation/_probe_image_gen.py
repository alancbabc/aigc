"""Minimal POST to Gitee POST /v1/images/generations — verify image API (does not print secrets)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import error, request


AIGC_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv_no_override(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        v = v.strip()
        if k and k not in os.environ:
            os.environ[k] = v


def main() -> int:
    load_dotenv_no_override(AIGC_ROOT / ".env")
    key = (os.environ.get("AIGC_GITEE_API_KEY") or "").strip()
    base = os.environ.get("AIGC_GITEE_BASE_URL", "https://ai.gitee.com/v1").rstrip("/")
    model = os.environ.get("AIGC_GITEE_IMAGE_MODEL", "kolors")
    url = f"{base}/images/generations"

    if not key:
        print("Gitee image API: skip (no AIGC_GITEE_API_KEY in env / aigc/.env)")
        return 1

    payload = json.dumps(
        {
            "prompt": "minimal solid blue gradient, test ping, no text",
            "model": model,
            "size": "512x512",
        }
    ).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    print(f"POST {url} (model={model})")
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
            print(f"  HTTP {resp.status} OK")
            data = body.get("data") or []
            if data and (data[0].get("b64_json") or data[0].get("url")):
                print("  Image API: usable (received image payload)")
            else:
                print("  Response keys:", list(body.keys()))
    except error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:400]
        print(f"  HTTP {e.code} {e.reason}")
        print("  ", err_body.replace("\n", " ")[:320])
        return 1 if e.code >= 500 else 0
    except OSError as e:
        print(f"  Network error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
