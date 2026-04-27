# FLUX Image Edit API config

import os


API_KEY = os.getenv("AIGC_GITEE_API_KEY", "")
BASE_URL = os.getenv("AIGC_GITEE_BASE_URL", "https://ai.gitee.com/v1")
API_URL = f"{BASE_URL}/images/edits"
