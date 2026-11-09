"""Per-user application settings (stored locally in %APPDATA%\\RedactR)."""

import json
import os

_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RedactR")
_FILE = os.path.join(_DIR, "config.json")


def load() -> dict:
    try:
        with open(_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save(cfg: dict):
    os.makedirs(_DIR, exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def default_projects_dir() -> str:
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(docs if os.path.isdir(docs) else os.path.expanduser("~"), "RedactR Projects")
