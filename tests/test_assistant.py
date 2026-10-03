"""Assistant flow with a fake planner (no network), and the voice helpers that need no microphone."""
import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from candor.assistant import Assistant
from candor.voice import audio_devices, multipart, pick_microphone

NOW = datetime.fromisoformat("2026-09-18T09:00:00-07:00")
SLACK = {"type": "slack.send_message", "args": {"to": "U03SARAHK", "text": "fix looks good"}}


class FakeCandor:
    def __init__(self, plans: dict[str, list[dict]]):
        self.plans, self.asked = plans, []
        self.people = [SimpleNamespace(slack_id="U03SARAHK", name="Sarah Kim")]
        self.corpus = SimpleNamespace(channels=[{"id": "C10RP", "name": "route-planner"}])

    def act(self, command, as_of):
        return self.plans[command]

    def ask(self, question, as_of):
        self.asked.append(question)
        return {"answer": "October 21.", "sources": ["SL-F-0164"], "abstained": False}


def audit(tmp_path):
    return [json.loads(l) for l in open(tmp_path / "audit.jsonl")]


def test_question_is_answered_from_memory_with_sources(tmp_path):
    bot = Assistant(FakeCandor({"launch?": [{"type": "memory.ask", "args": {"question": "launch date"}}]}), outbox=tmp_path)
    reply = bot.handle("launch?", NOW)
    assert reply.text == "October 21." and reply.sources == ["SL-F-0164"] and not reply.needs_yes


def test_action_waits_for_yes_and_dry_run_writes_no_outbox(tmp_path):
    bot = Assistant(FakeCandor({"msg": [SLACK]}), outbox=tmp_path)
    reply = bot.handle("msg", NOW)
    assert reply.needs_yes and "Sarah Kim (U03SARAHK)" in reply.text
    assert "Dry run" in bot.handle("yes", NOW).text
    assert not (tmp_path / "slack.send_message.jsonl").exists()
    assert audit(tmp_path)[-1]["decision"] == "dry run"


def test_execute_writes_sandbox_outbox_only_after_yes(tmp_path):
    bot = Assistant(FakeCandor({"msg": [SLACK]}), execute=True, outbox=tmp_path)
    bot.handle("msg", NOW)
    assert not (tmp_path / "slack.send_message.jsonl").exists()
    bot.handle("yes", NOW)
    assert [json.loads(l) for l in open(tmp_path / "slack.send_message.jsonl")] == [SLACK["args"]]


def test_no_declines_and_is_audited(tmp_path):
    bot = Assistant(FakeCandor({"msg": [SLACK]}), execute=True, outbox=tmp_path)
    bot.handle("msg", NOW)
    assert "won't" in bot.handle("no", NOW).text
    assert not (tmp_path / "slack.send_message.jsonl").exists()
    assert audit(tmp_path)[-1]["decision"] == "declined"


def test_destructive_command_is_never_run(tmp_path):
    plan = [{"type": "confirm", "args": {"summary": "Delete every email from Marcus Webb?"}}]
    bot = Assistant(FakeCandor({"delete": plan}), execute=True, outbox=tmp_path)
    assert bot.handle("delete", NOW).needs_yes
    assert "Nothing was deleted" in bot.handle("yes", NOW).text
    assert [p.name for p in tmp_path.iterdir()] == ["audit.jsonl"]


def test_clarify_goes_back_to_the_user(tmp_path):
    plan = [{"type": "clarify", "args": {"question": "Which Sarah: Sarah Kim or Sarah Patel?"}}]
    reply = Assistant(FakeCandor({"msg sarah": plan}), outbox=tmp_path).handle("msg sarah", NOW)
    assert reply.text == "Which Sarah: Sarah Kim or Sarah Patel?" and not reply.needs_yes


LISTING = """[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] FaceTime HD Camera
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] BlackHole 2ch
[AVFoundation indev @ 0x1] [1] AR~iPhone15Pro Microphone
[AVFoundation indev @ 0x1] [2] MacBook Air Microphone
[in#0 @ 0x2] Error opening input: Input/output error"""


def test_microphone_is_chosen_by_name_not_index():
    devices = audio_devices(LISTING)
    assert devices == [(0, "BlackHole 2ch"), (1, "AR~iPhone15Pro Microphone"), (2, "MacBook Air Microphone")]
    assert pick_microphone(devices) == (2, "MacBook Air Microphone")
    assert pick_microphone(devices, "iphone") == (1, "AR~iPhone15Pro Microphone")
    with pytest.raises(RuntimeError):
        pick_microphone([(0, "BlackHole 2ch")])


def test_multipart_carries_fields_and_file(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....WAVE")
    body, content_type = multipart({"model": "whisper"}, "file", wav)
    boundary = content_type.split("boundary=")[1]
    assert body.startswith(f"--{boundary}".encode()) and body.endswith(f"--{boundary}--\r\n".encode())
    assert b'name="model"\r\n\r\nwhisper' in body and b'filename="a.wav"' in body and b"RIFF....WAVE" in body
