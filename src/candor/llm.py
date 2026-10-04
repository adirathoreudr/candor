"""One LLM interface over two backends, with a content-addressed cache.

- `openai`: any OpenAI-compatible chat endpoint (NVIDIA NIM by default), configured from .env.
- `claude-cli`: the local Claude Code CLI, run as a plain isolated model the same way
  eval_harness/llm.py runs the judge. No key needed.

Every call is temperature 0 and cached by a hash of everything that affects the output, so a
rerun replays the same answers with no network and no key. The cache lives in artifacts/llm_cache
and is committed.
"""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from candor import config


MAX_RETRY_WAIT = 120   # seconds; a provider asking us to wait longer is out of quota, not briefly busy


class LLMError(RuntimeError):
    """The model gave no usable reply for this request (after retries). Callers can fall back per item."""


class LLMUnavailable(LLMError):
    """No usable backend: missing key or exhausted quota. Raised once, with a message a human can act on."""


class _Truncated(Exception):
    """Empty content because the model spent the whole token budget (finish_reason=length)."""


@dataclass
class Usage:
    calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    failures: list = field(default_factory=list)

    def summary(self) -> str:
        return (f"llm: {self.calls} calls, {self.cache_hits} from cache, "
                f"{self.prompt_tokens} prompt + {self.completion_tokens} completion tokens, {self.seconds:.0f}s")


_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def parse_json(text: str) -> dict:
    """The first JSON object in a model reply (tolerates code fences and reasoning tags)."""
    text = _THINK_RE.sub("", text or "")
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("reply JSON is not an object")
    return obj


class LLM:
    def __init__(self, backend: str = None, model: str = None, max_tokens: int = 1200,
                 timeout: int = 180, retries: int = 6):
        self.backend = backend or config.LLM_BACKEND
        self.model = model or config.LLM_MODEL
        self.max_tokens, self.timeout, self.retries = max_tokens, timeout, retries
        self.usage = Usage()
        self.cache_dir = config.ARTIFACTS / "llm_cache"

    def check(self) -> None:
        if self.backend == "openai":
            missing = [k for k, v in (("LLM_BASE_URL", config.LLM_BASE_URL), ("LLM_API_KEY", config.LLM_API_KEY),
                                      ("LLM_MODEL", self.model)) if not v]
            if missing:
                raise LLMUnavailable(f"LLM key missing: set {', '.join(missing)} in .env (see .env.example)")
        elif self.backend == "claude-cli":
            if subprocess.run(["which", "claude"], capture_output=True).returncode != 0:
                raise LLMUnavailable("LLM_BACKEND=claude-cli but the `claude` CLI is not on PATH")
        else:
            raise LLMUnavailable(f"unknown LLM_BACKEND {self.backend!r}: use openai or claude-cli")

    def _key(self, system: str, user: str) -> str:
        blob = json.dumps({"backend": self.backend, "model": self.model, "system": system, "user": user,
                           "temperature": 0, "max_tokens": self.max_tokens}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    def complete(self, system: str, user: str) -> str:
        key = self._key(system, user)
        path = self.cache_dir / key[:2] / f"{key}.json"
        if path.exists():
            self.usage.cache_hits += 1
            return json.loads(path.read_text())["reply"]
        self.check()
        started = time.time()
        reply = self._call(system, user)
        self.usage.calls += 1
        self.usage.seconds += time.time() - started
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"backend": self.backend, "model": self.model, "reply": reply}, indent=1))
        return reply

    def complete_json(self, system: str, user: str) -> dict:
        reply = self.complete(system, user)
        try:
            return parse_json(reply)
        except ValueError:
            # One repair attempt with the bad reply shown; a different prompt means a different cache key.
            fixed = self.complete(system, user + "\n\nYour previous reply was not valid JSON:\n" + reply[:2000] +
                                  "\n\nReply again with only the JSON object.")
            try:
                return parse_json(fixed)
            except ValueError as e:
                raise LLMError(f"{self.model}: reply was not valid JSON after one repair") from e

    def _call(self, system: str, user: str) -> str:
        budget = self.max_tokens
        for attempt in range(self.retries):
            try:
                if self.backend == "claude-cli":
                    return self._claude_cli(system, user)
                return self._openai(system, user, budget)
            except _Truncated as e:
                # Same request again would truncate again (temperature 0): retry once with double the budget.
                if budget > self.max_tokens:
                    raise LLMError(f"{self.model}: no reply within {budget} tokens") from e
                budget *= 2
                continue
            except (urllib.error.URLError, TimeoutError, subprocess.TimeoutExpired, RuntimeError) as e:
                if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                    detail = e.read().decode(errors="replace")
                    after = e.headers.get("retry-after", "")
                    long_wait = after.replace(".", "").isdigit() and float(after) > MAX_RETRY_WAIT
                    if long_wait or ("quota" in detail.lower() and "per day" in detail.lower()) \
                            or re.search(r"retry in \d+h", detail):
                        # A daily quota does not come back within any sane retry window: stop now, say why.
                        detail = re.sub(r" in organization `[^`]*`", "", detail)   # keep account ids off screen
                        reason = re.search(r"(Quota exceeded|Rate limit reached)[^\n\"]{0,200}", detail)
                        raise LLMUnavailable(f"LLM quota exhausted for {self.model}"
                                             f"{f' (frees in {float(after) / 60:.0f} min)' if long_wait else ''}: "
                                             f"{reason.group(0) if reason else detail[:160]}") from e
                retryable = not isinstance(e, urllib.error.HTTPError) or e.code in (408, 409, 425, 429, 500, 502, 503, 504)
                if not retryable or attempt == self.retries - 1:
                    self.usage.failures.append(str(e)[:200])
                    raise LLMError(f"{self.model}: {type(e).__name__} {str(e)[:160]}") from e
                wait = 2 ** attempt * 3
                if isinstance(e, urllib.error.HTTPError) and e.headers.get("retry-after", "").replace(".", "").isdigit():
                    wait = max(wait, float(e.headers["retry-after"]) + 1)   # provider says exactly when
                print(f"llm: {type(e).__name__} {str(e)[:80]}; retry in {wait}s", file=sys.stderr)
                time.sleep(wait)
        raise LLMError(f"{self.model}: no reply after {self.retries} attempts")

    def _openai(self, system: str, user: str, max_tokens: int | None = None) -> str:
        body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens or self.max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        req = urllib.request.Request(f"{config.LLM_BASE_URL}/chat/completions", data=json.dumps(body).encode(),
                                     # Explicit User-Agent: some providers' edge (Groq's Cloudflare, error 1010)
                                     # reject Python's default "Python-urllib" agent with a 403.
                                     headers={"Authorization": f"Bearer {config.LLM_API_KEY}",
                                              "Content-Type": "application/json", "Accept": "application/json",
                                              "User-Agent": "candor/0.1"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read())
        usage = out.get("usage") or {}
        self.usage.prompt_tokens += usage.get("prompt_tokens") or 0
        self.usage.completion_tokens += usage.get("completion_tokens") or 0
        content = out["choices"][0]["message"].get("content")
        if not content and out["choices"][0].get("finish_reason") == "length":
            raise _Truncated()
        if not content:
            raise RuntimeError(f"empty completion (finish_reason={out['choices'][0].get('finish_reason')})")
        return content

    def _claude_cli(self, system: str, user: str) -> str:
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(
                ["claude", "-p", "--model", self.model or "haiku", "--tools", "", "--setting-sources", "",
                 "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence",
                 "--system-prompt", system],
                input=user, capture_output=True, text=True, timeout=self.timeout, cwd=cwd)
        if proc.returncode != 0:
            raise RuntimeError(f"claude-cli failed: {proc.stderr.strip()[:200]}")
        return proc.stdout.strip()
