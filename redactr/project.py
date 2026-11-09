"""A project = one folder that holds the mapping vault, sanitized copies, reports
and restored files.  Keep using the same project for a piece of work so the
same real name always gets the same fictional name, and so AI answers can be
restored."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from .levels import LEVELS_BY_KEY, Profile, default_custom_profile
from .vault import VAULT_FILENAME, Vault

PROJECT_FILE = "redactr-project.json"


class Project:
    def __init__(self, folder: str, settings: dict, vault: Vault, password: str | None):
        self.folder = folder
        self.settings = settings
        self.vault = vault
        self.password = password or None

    # ------------------------------------------------------------- paths
    @property
    def name(self):
        return self.settings.get("name") or os.path.basename(self.folder)

    def sub(self, name: str) -> str:
        p = os.path.join(self.folder, name)
        os.makedirs(p, exist_ok=True)
        return p

    @property
    def sanitized_dir(self):
        return self.sub("sanitized")

    @property
    def reports_dir(self):
        return self.sub("reports")

    @property
    def restored_dir(self):
        return self.sub("restored")

    @property
    def vault_path(self):
        return os.path.join(self.folder, VAULT_FILENAME)

    # ------------------------------------------------------------- lifecycle
    @staticmethod
    def is_project(folder: str) -> bool:
        return os.path.isfile(os.path.join(folder, PROJECT_FILE))

    @staticmethod
    def needs_password(folder: str) -> bool:
        vp = os.path.join(folder, VAULT_FILENAME)
        return os.path.isfile(vp) and Vault.is_encrypted(vp)

    @classmethod
    def create(cls, folder: str, name: str = "", password: str | None = None) -> "Project":
        os.makedirs(folder, exist_ok=True)
        settings = {"name": name or os.path.basename(os.path.abspath(folder)),
                    "created": datetime.now().isoformat(timespec="seconds"),
                    "level": "L3", "custom_profile": json.loads(default_custom_profile().to_json()),
                    "encrypted": bool(password)}
        p = cls(folder, settings, Vault(), password)
        p.save()
        for d in ("sanitized", "reports", "restored"):
            p.sub(d)
        return p

    @classmethod
    def open(cls, folder: str, password: str | None = None) -> "Project":
        with open(os.path.join(folder, PROJECT_FILE), encoding="utf-8") as fh:
            settings = json.load(fh)
        vp = os.path.join(folder, VAULT_FILENAME)
        vault = Vault.load(vp, password) if os.path.isfile(vp) else Vault()
        return cls(folder, settings, vault, password)

    def save(self):
        self.settings["encrypted"] = bool(self.password)
        with open(os.path.join(self.folder, PROJECT_FILE), "w", encoding="utf-8") as fh:
            json.dump(self.settings, fh, indent=2, ensure_ascii=False)
        self.vault.save(self.vault_path, self.password)

    # ------------------------------------------------------------- profiles
    def custom_profile(self) -> Profile:
        d = self.settings.get("custom_profile")
        return Profile.from_dict(d) if d else default_custom_profile()

    def set_custom_profile(self, p: Profile):
        self.settings["custom_profile"] = json.loads(p.to_json())

    def profile(self, key: str | None = None) -> Profile:
        key = key or self.settings.get("level", "L3")
        if key == "CUSTOM":
            return self.custom_profile()
        base = LEVELS_BY_KEY[key]
        # project-wide custom terms / allow list also apply to the built-in levels
        cp = self.custom_profile()
        return Profile(**{**base.__dict__, "custom_terms": list(cp.custom_terms),
                          "allow_list": list(cp.allow_list), "custom_patterns": list(cp.custom_patterns),
                          "categories": list(base.categories), "style": dict(base.style)})


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_filename(s: str) -> str:
    return re.sub(r"[^\w.-]+", "_", s)[:80]
