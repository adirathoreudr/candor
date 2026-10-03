"""Make raw text safe to store: secrets are redacted and hidden markup is removed.

Runs once at ingest, so no later layer (index, LLM prompt, answer) ever sees a secret value.
"""
import re

REDACTED = "[REDACTED SECRET]"

# Well-known credential shapes. Each pattern matches the secret value only.
_TOKEN_PATTERNS = [
    r"\bsk-[A-Za-z0-9_\-]{16,}",            # OpenAI / Anthropic style keys
    r"\bgh[pousr]_[A-Za-z0-9]{20,}",         # GitHub tokens
    r"\bxox[abprs]-[A-Za-z0-9\-]{10,}",      # Slack tokens
    r"\bAKIA[0-9A-Z]{16}\b",                 # AWS access key id
    r"\bAIza[0-9A-Za-z_\-]{30,}",            # Google API key
    r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",  # JWT
]
_TOKEN_RE = re.compile("|".join(_TOKEN_PATTERNS))

# user:password@host inside a URL: keep the user and host, drop the password.
_URL_CREDS_RE = re.compile(r"(\b[a-z][a-z0-9+.\-]*://[^\s:/@]+:)[^\s@/]+(@)", re.I)

# ENV_STYLE_KEY=value / KEY: value (uppercase, so prose like "theme tokens: done" is untouched),
# plus a lowercase "password: value".
_ASSIGNMENT_RE = re.compile(
    r"(\b[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|APIKEY|PRIVATE_KEY)[A-Z0-9_]*\b\s*[:=]\s*"
    r"|(?i:\bpassword\b)\s*[:=]\s*)"
    r"([\"']?)[^\s\"',]+\2")

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def redact_secrets(text: str) -> str:
    text = _TOKEN_RE.sub(REDACTED, text)
    text = _URL_CREDS_RE.sub(rf"\1{REDACTED}\2", text)
    return _ASSIGNMENT_RE.sub(rf"\1{REDACTED}", text)


def strip_hidden_markup(text: str) -> tuple[str, bool]:
    """Remove HTML comments: a reader never sees them, so they are not part of what was said.
    Returns the cleaned text and whether anything was removed."""
    cleaned = _HTML_COMMENT_RE.sub("", text)
    return cleaned, cleaned != text


def clean(text: str | None) -> tuple[str, bool]:
    """Full sanitizing pass. Returns (text, had_hidden_markup)."""
    text, hidden = strip_hidden_markup(text or "")
    return redact_secrets(text), hidden
