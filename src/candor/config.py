"""Paths and settings. Everything overridable from the environment."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader: KEY=value lines; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("CANDOR_DATA", ROOT / "data"))
ARTIFACTS = ROOT / "artifacts"
PROMPTS = ROOT / "prompts"
MODEL_CACHE = Path(os.environ.get("CANDOR_MODEL_CACHE", Path.home() / ".cache/candor/models"))
TIMEZONE = "America/Los_Angeles"

# Sized for an 8 GB laptop: small model, small batches, few threads. Measured: the library default
# (batch 256, all cores, bge-base) froze a MacBook Air M2.
EMBED_MODEL = os.environ.get("CANDOR_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_THREADS = int(os.environ.get("CANDOR_EMBED_THREADS", "2"))
EMBED_BATCH = int(os.environ.get("CANDOR_EMBED_BATCH", "8"))
EMBED_MAX_CHARS = 2000   # the model reads 512 tokens at most; longer text only costs memory
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", str(EMBED_THREADS))

LLM_BACKEND = os.environ.get("LLM_BACKEND", "openai")      # openai | claude-cli
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")                         # answers
# Optional per-role models. On free tiers each model has its own daily quota, so splitting roles
# across models multiplies the budget. Unset means the answer model does everything.
LLM_MODEL_PLAN = os.environ.get("LLM_MODEL_PLAN", "") or LLM_MODEL
LLM_MODEL_RERANK = os.environ.get("LLM_MODEL_RERANK", "") or LLM_MODEL
