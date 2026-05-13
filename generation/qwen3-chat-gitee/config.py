# Gitee Serverless Qwen3 text chat (non-streaming)

import os

API_KEY = os.getenv("AIGC_GITEE_API_KEY", "") or os.getenv("GITEE_API_TOKEN", "")
BASE_URL = os.getenv("AIGC_GITEE_BASE_URL", "https://ai.gitee.com/v1").rstrip("/")
API_URL = f"{BASE_URL}/chat/completions"
DEFAULT_MODEL = os.getenv("AIGC_QWEN3_MODEL", "Qwen3.5-122B-A10B")
