# MinerU2.5 OCR API config

import os


API_KEY = os.getenv("AIGC_GITEE_API_KEY", "")
BASE_URL = os.getenv("AIGC_GITEE_BASE_URL", "https://ai.gitee.com/v1")
TASK_BASE_URL = os.getenv("AIGC_GITEE_TASK_BASE_URL", "https://ai.gitee.com/api/v1/task")
API_URL = f"{BASE_URL}/async/documents/parse"
