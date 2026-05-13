"""One-off probe: reachability for generation/ APIs. Does not print secrets."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

# Repo root: .../jinyi/aigc
AIGC_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv_no_override(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


def try_get(url: str, headers: dict[str, str] | None, timeout: float) -> tuple[bool, int | None, str]:
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout, allow_redirects=True)
        body = (r.text or "")[:100].replace("\n", " ")
        return True, r.status_code, body
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"[:120]


def main() -> None:
    load_dotenv_no_override(AIGC_ROOT / ".env")

    rows: list[tuple[str, str, str, bool, int | None, str]] = []

    local_urls = [
        ("qwen-image-local", "script/env default", f"{os.environ.get('QWEN_IMAGE_LOCAL_BASE_URL', 'http://10.0.180.14:9000').rstrip('/')}/"),
        ("qwen-image-local", "example.json", "http://10.42.1.2:9000/"),
        ("qwen-image-local", "SKILL.md", "http://10.42.1.1:9000/"),
        ("qwen-tts-local", "script default", f"{os.environ.get('QWEN_TTS_LOCAL_BASE_URL', 'http://10.0.180.14:7786').rstrip('/')}/"),
        ("qwen-tts-local", "SKILL.md", "http://10.42.1.2:9200/"),
        ("ltx23-video", "generate_a2v.sh default", f"{os.environ.get('LTX23_BASE_URL', 'http://10.0.180.14:80').rstrip('/')}/"),
        ("ltx23-video", "SKILL.md", "http://10.0.180.14:8000/"),
        ("localhost", "image :9000", "http://127.0.0.1:9000/"),
        ("localhost", "tts :7786", "http://127.0.0.1:7786/"),
        ("localhost", "ltx :8000", "http://127.0.0.1:8000/"),
    ]

    for family, note, url in local_urls:
        ok, code, extra = try_get(url, None, 8)
        rows.append((family, f"{note} -> {url}", url, ok, code, extra))

    gitee_base = os.environ.get("AIGC_GITEE_BASE_URL", "https://ai.gitee.com/v1").rstrip("/")
    gitee_public = [
        ("gitee (shared)", "GET /v1/", f"{gitee_base}/"),
        ("gitee (shared)", "GET /v1/models", f"{gitee_base}/models"),
    ]
    for family, note, url in gitee_public:
        ok, code, extra = try_get(url, None, 15)
        rows.append((family, note, url, ok, code, extra))

    api_key = (os.environ.get("AIGC_GITEE_API_KEY") or os.environ.get("GITEE_API_TOKEN") or "").strip()
    if api_key:
        ok, code, extra = try_get(
            f"{gitee_base}/models",
            {"Authorization": f"Bearer {api_key}"},
            20,
        )
        rows.append(("gitee (auth)", "GET /v1/models with Bearer", f"{gitee_base}/models", ok, code, extra))
    else:
        rows.append(("gitee (auth)", "no key in env or aigc/.env", "", False, None, "skipped"))

    # Map to generation subdirs (documentation)
    generation_apis = [
        "qwen3-chat-gitee -> Gitee POST /v1/messages",
        "qwen-image-2512 -> Gitee POST /v1/images/generations",
        "flux-text-to-image -> Gitee POST /v1/images/generations",
        "flux-image-edit -> Gitee POST /v1/images/edits",
        "mineru25-ocr -> Gitee POST /v1/async/documents/parse + task API",
        "ltx23-video (hq) -> Gitee POST /v1/async/videos/image-to-video",
        "qwen-image-local -> self-hosted POST /submit",
        "qwen-tts-local -> self-hosted POST /submit",
        "ltx23-video (a2v) -> self-hosted POST /submit (LTX23_BASE_URL)",
    ]

    print("generation/ API probe (reachability; 401 still means host is up)\n")
    print(f"{'family':<22} {'ok':<4} {'code':<6} detail")
    print("-" * 100)
    for family, detail, url, ok, code, extra in rows:
        code_s = str(code) if code is not None else "—"
        ok_s = "yes" if ok else "no"
        line = f"{family:<22} {ok_s:<4} {code_s:<6} {detail}"
        if url:
            line += f" | {extra}"
        else:
            line += f" | {extra}"
        print(line)

    print("\nSubmodules using same Gitee base (need AIGC_GITEE_API_KEY for real calls):")
    for line in generation_apis:
        if line.startswith("qwen") and "Gitee" in line:
            print(" ", line)

    gitee_ok = any(
        r[3] and r[4] in (200, 401, 403)
        for r in rows
        if r[0].startswith("gitee (shared)") and r[2].endswith("/models")
    )
    if not gitee_ok:
        gitee_ok = any(r[3] for r in rows if "ai.gitee.com" in r[2])

    print("\nSummary:")
    print(
        "  Gitee ai.gitee.com:",
        "reachable (got HTTP response)" if any(r[3] for r in rows if "gitee.com" in r[2]) else "unreachable",
    )
    if api_key:
        auth_row = [r for r in rows if r[0] == "gitee (auth)" and r[2]]
        if auth_row and auth_row[0][4] == 200:
            print("  Gitee with key: authorized (200 on /models)")
        elif auth_row:
            print(f"  Gitee with key: HTTP {auth_row[0][4]} — check quota/key")
    else:
        print("  Gitee with key: not tested (no API key loaded)")

    local_ok = [r for r in rows if r[0] in ("qwen-image-local", "qwen-tts-local", "ltx23-video", "localhost") and r[3]]
    print(f"  Self-hosted: {len(local_ok)} endpoint(s) responded (see table above)")


if __name__ == "__main__":
    sys.exit(main() or 0)
