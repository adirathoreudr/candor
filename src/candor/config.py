"""Paths and settings. Everything overridable from the environment."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CANDOR_DATA", ROOT / "data"))
TIMEZONE = "America/Los_Angeles"
