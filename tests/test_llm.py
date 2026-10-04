"""LLM client failure handling, with the network faked."""
import io
import urllib.error
from email.message import Message

import pytest

from candor import llm as llm_mod
from candor.llm import LLM, LLMError, LLMUnavailable


def http_429(retry_after: str, body: str) -> urllib.error.HTTPError:
    headers = Message()
    headers["retry-after"] = retry_after
    return urllib.error.HTTPError("https://x", 429, "Too Many Requests", headers, io.BytesIO(body.encode()))


def test_long_retry_after_stops_with_a_clear_message(monkeypatch, tmp_path):
    client = LLM(backend="openai", model="m")
    client.cache_dir = tmp_path
    monkeypatch.setattr(llm_mod.config, "LLM_BASE_URL", "https://x")
    monkeypatch.setattr(llm_mod.config, "LLM_API_KEY", "k")
    monkeypatch.setattr(client, "_openai", lambda *a: (_ for _ in ()).throw(
        http_429("1780", '{"error":{"message":"Rate limit reached for model m on tokens per day (TPD)"}}')))
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: pytest.fail("must not wait out a daily quota"))
    with pytest.raises(LLMUnavailable, match=r"quota exhausted for m \(frees in 30 min\): Rate limit reached"):
        client.complete("s", "u")


def test_short_retry_after_waits_then_succeeds(monkeypatch, tmp_path):
    client = LLM(backend="openai", model="m")
    client.cache_dir = tmp_path
    monkeypatch.setattr(llm_mod.config, "LLM_BASE_URL", "https://x")
    monkeypatch.setattr(llm_mod.config, "LLM_API_KEY", "k")
    calls, waits = [], []

    def flaky(*a):
        calls.append(1)
        if len(calls) == 1:
            raise http_429("5", "busy")
        return '{"ok": true}'

    monkeypatch.setattr(client, "_openai", flaky)
    monkeypatch.setattr(llm_mod.time, "sleep", waits.append)
    assert client.complete_json("s", "u") == {"ok": True}
    assert waits == [6.0]                       # retry-after + 1 s
    assert client.complete_json("s", "u") == {"ok": True} and len(calls) == 2   # second call is a cache hit


def test_missing_key_is_one_clear_error(monkeypatch):
    monkeypatch.setattr(llm_mod.config, "LLM_API_KEY", "")
    with pytest.raises(LLMUnavailable, match="LLM key missing"):
        LLM(backend="openai", model="m").check()


def test_truncated_reply_retries_once_with_more_tokens_then_gives_a_clean_error(monkeypatch, tmp_path):
    client = LLM(backend="openai", model="m", max_tokens=100)
    client.cache_dir = tmp_path
    monkeypatch.setattr(llm_mod.config, "LLM_BASE_URL", "https://x")
    monkeypatch.setattr(llm_mod.config, "LLM_API_KEY", "k")
    budgets = []

    def truncated(system, user, budget):
        budgets.append(budget)
        raise llm_mod._Truncated()

    monkeypatch.setattr(client, "_openai", truncated)
    with pytest.raises(LLMError, match="no reply within 200 tokens"):
        client.complete("s", "u")
    assert budgets == [100, 200]


def test_unparsable_json_after_repair_is_an_llm_error(monkeypatch, tmp_path):
    client = LLM(backend="openai", model="m")
    client.cache_dir = tmp_path
    monkeypatch.setattr(llm_mod.config, "LLM_BASE_URL", "https://x")
    monkeypatch.setattr(llm_mod.config, "LLM_API_KEY", "k")
    monkeypatch.setattr(client, "_openai", lambda *a: "not json at all")
    with pytest.raises(LLMError, match="not valid JSON"):
        client.complete_json("s", "u")
