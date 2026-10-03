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

# The setup the committed outputs were produced with: Groq's free tier, one model per role (each model
# has its own daily quota). Model names are not secrets; defaulting them means a clean clone without a
# key still hits the committed LLM cache and reproduces the outputs exactly. Only LLM_API_KEY is needed
# for new questions. Setting LLM_MODEL (another provider) makes it the default for every role.
_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_MODELS = {"answer": "openai/gpt-oss-120b", "plan": "openai/gpt-oss-20b",
                   "rerank": "qwen/qwen3.8-27b", "act": "openai/gpt-oss-20b"}

LLM_BACKEND = os.environ.get("LLM_BACKEND", "openai")      # openai | claude-cli
if LLM_BACKEND == "claude-cli":   # the local CLI takes its own model names
    _DEFAULT_MODELS = dict.fromkeys(_DEFAULT_MODELS, "haiku")
LLM_BASE_URL = (os.environ.get("LLM_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
_custom = bool(os.environ.get("LLM_MODEL"))
LLM_MODEL = os.environ.get("LLM_MODEL") or _DEFAULT_MODELS["answer"]   # answers


def _role(name: str) -> str:
    return os.environ.get(f"LLM_MODEL_{name.upper()}") or (LLM_MODEL if _custom else _DEFAULT_MODELS[name])


LLM_MODEL_PLAN = _role("plan")
LLM_MODEL_RERANK = _role("rerank")
LLM_MODEL_ACT = _role("act")
