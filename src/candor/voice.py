"""Voice in and out for the assistant, macOS.

- In: push-to-talk recording with ffmpeg (AVFoundation), 16 kHz mono WAV, from the microphone chosen
  by name (the first audio device is often a virtual one, e.g. BlackHole), then speech-to-text through
  the OpenAI-compatible /audio/transcriptions endpoint (Groq Whisper by default, same key as the LLM).
- Out: macOS `say`.
"""
import json
import os
import re
import subprocess
import tempfile
import urllib.request
import uuid
from pathlib import Path

from candor import config
from candor.llm import LLMUnavailable

STT_MODEL = os.environ.get("CANDOR_STT_MODEL") or "whisper-large-v3-turbo"   # empty in .env means default
_DEVICE_RE = re.compile(r"\[(\d+)\] (.+)$")


def audio_devices(listing: str) -> list[tuple[int, str]]:
    """Parse `ffmpeg -f avfoundation -list_devices true -i ""` output into [(index, name)] for audio inputs."""
    devices, in_audio = [], False
    for line in listing.splitlines():
        if "audio devices" in line:
            in_audio = True
            continue
        if in_audio:
            hit = _DEVICE_RE.search(line)
            if hit:
                devices.append((int(hit.group(1)), hit.group(2).strip()))
            elif "devices" in line:
                break
    return devices


def pick_microphone(devices: list[tuple[int, str]], wanted: str | None = None) -> tuple[int, str]:
    """CANDOR_MIC (substring) if set, else the built-in mic, else the first device named like a microphone."""
    wanted = (wanted or os.environ.get("CANDOR_MIC") or "").lower()
    for rule in ([lambda n: wanted in n.lower()] if wanted else []) + [
            lambda n: "macbook" in n.lower() and "microphone" in n.lower(),
            lambda n: "built-in" in n.lower(),
            lambda n: "microphone" in n.lower() and "iphone" not in n.lower()]:
        for index, name in devices:
            if rule(name):
                return index, name
    raise RuntimeError(f"no microphone found among audio devices: {[n for _, n in devices]}; set CANDOR_MIC")


def microphone() -> tuple[int, str]:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                         capture_output=True, text=True).stderr
    return pick_microphone(audio_devices(out))


def record(path: Path, device: int) -> None:
    """Record until the user presses Enter."""
    proc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "avfoundation", "-i", f":{device}",
                             "-ac", "1", "-ar", "16000", "-y", str(path)], stdin=subprocess.PIPE)
    input("  recording... press Enter to stop ")
    proc.communicate(b"q", timeout=10)   # 'q' tells ffmpeg to finish the file cleanly


def multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode() for k, v in fields.items()]
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{file_path.name}\"\r\n"
                 f"Content-Type: audio/wav\r\n\r\n".encode() + file_path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def vocabulary(names: list[str]) -> str:
    """Whisper's prompt field biases recognition toward these spellings (people, channels, products)."""
    return ", ".join(dict.fromkeys(n for n in names if n))[:800]


def transcribe(path: Path, prompt: str = "") -> str:
    if not (config.LLM_BASE_URL and config.LLM_API_KEY):
        raise LLMUnavailable("voice needs LLM_BASE_URL and LLM_API_KEY for speech-to-text (see .env.example)")
    fields = {"model": STT_MODEL, "language": "en", "response_format": "json", "temperature": "0"}
    if prompt:
        fields["prompt"] = prompt
    body, content_type = multipart(fields, "file", path)
    req = urllib.request.Request(f"{config.LLM_BASE_URL}/audio/transcriptions", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": content_type,
                                          "User-Agent": "candor/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["text"].strip()


def speak(text: str) -> None:
    spoken = re.sub(r"\b[A-Z]{2,}-[A-Z0-9#-]+\b", "", text)        # drop record ids from speech
    subprocess.run(["say", spoken[:600]], check=False)


def listen(device: int, prompt: str = "") -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "command.wav"
        record(path, device)
        return transcribe(path, prompt)
