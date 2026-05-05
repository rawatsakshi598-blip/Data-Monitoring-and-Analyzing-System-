import os

# ── Load .env file ──
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "db", "custom.db")
    ),
)
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
LLM_ENABLED = bool(LLM_API_KEY)
CHUNKS_DIR = os.environ.get("CHUNKS_DIR", "/tmp/dataguard_chunks")
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", str(100 * 1024 * 1024)))
MAX_COLUMNS = int(os.environ.get("MAX_COLUMNS", "1000"))
MAX_ROWS = int(os.environ.get("MAX_ROWS", str(10_000_000)))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))


class _DBConfig:
    def __init__(self):
        self.url = f"sqlite:///{DB_PATH}"


class _LLMConfig:
    def __init__(self):
        self.base_url = LLM_BASE_URL
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "8192"))
        self.temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1"))


class _ServerConfig:
    def __init__(self):
        self.port = int(os.environ.get("SERVER_PORT", "3001"))
        self.host = os.environ.get("SERVER_HOST", "0.0.0.0")
        self.cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")


class Config:
    def __init__(self):
        self.db = _DBConfig()
        self.llm = _LLMConfig()
        self.server = _ServerConfig()

    @classmethod
    def from_env(cls):
        return cls()


def get_llm_status() -> dict:
    # Count fallback providers
    fallbacks = 0
    for i in range(1, 6):
        if os.environ.get(f"LLM_FALLBACK_{i}_API_KEY", ""):
            fallbacks += 1
    return {
        "configured": LLM_ENABLED,
        "provider": (
            LLM_BASE_URL.split("//")[1].split(".")[0]
            if "://" in LLM_BASE_URL
            else "custom"
        ),
        "model": LLM_MODEL,
        "fallbacks": fallbacks,
        "total_providers": (1 if LLM_ENABLED else 0) + fallbacks,
    }
