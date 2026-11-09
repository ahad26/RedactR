"""The mapping vault: remembers every original -> fictional replacement so the
process can be reversed later.  Optionally encrypted with a password.
"""

from __future__ import annotations

import base64
import json
import os
import random
import re
from datetime import datetime
from urllib.parse import urlsplit

from .categories import CATEGORIES
from .levels import REALISTIC, TOKEN
from .wordlists import (AMBIGUOUS_FIRST, COMMON_WORDS, FIRST_NAMES, ORG_SUFFIXES, STREET_SUFFIXES,
                        SURROGATE_CITY_LIST, SURROGATE_FIRST, SURROGATE_LAST, SURROGATE_ORG_CORE,
                        SURROGATE_STREETS, US_STATE_CODES)

VAULT_FILENAME = "mapping.redactr-vault"
_rng = random.SystemRandom()
AREA_CODES = [201, 212, 213, 305, 312, 404, 415, 503, 512, 602, 617, 646, 702, 713, 718, 801, 818, 917, 919, 972]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()


class VaultError(Exception):
    pass


class Vault:
    def __init__(self, data: dict | None = None):
        self.data = data or {
            "version": 1,
            "created": datetime.now().isoformat(timespec="seconds"),
            "entries": {},     # norm(original) -> {original, category, replacement, style, components:[[o, r], ...]}
            "first": {},       # first-name component map  (lower original -> surrogate)
            "last": {},        # last-name component map
            "orgcore": {},     # organisation core map
            "domain": {},      # domain map
            "counters": {},
        }
        self.dirty = False

    # ----------------------------------------------------------------- persistence
    def save(self, path: str, password: str | None = None):
        payload = json.dumps(self.data, ensure_ascii=False, indent=1).encode("utf-8")
        if password:
            salt = os.urandom(16)
            token = _fernet(password, salt).encrypt(payload)
            doc = {"redactr_vault": 1, "encrypted": True, "salt": base64.b64encode(salt).decode(),
                   "data": token.decode()}
        else:
            doc = {"redactr_vault": 1, "encrypted": False, "data": self.data}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        self.dirty = False

    @staticmethod
    def is_encrypted(path: str) -> bool:
        with open(path, encoding="utf-8") as fh:
            return bool(json.load(fh).get("encrypted"))

    @classmethod
    def load(cls, path: str, password: str | None = None) -> "Vault":
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if "redactr_vault" not in doc:
            raise VaultError("Not a ЯedactR vault file.")
        if doc.get("encrypted"):
            if not password:
                raise VaultError("This vault is password protected.")
            try:
                raw = _fernet(password, base64.b64decode(doc["salt"])).decrypt(doc["data"].encode())
            except Exception as exc:  # cryptography.fernet.InvalidToken
                raise VaultError("Wrong password for this vault.") from exc
            data = json.loads(raw.decode("utf-8"))
        else:
            data = doc["data"]
        for k in ("entries", "first", "last", "orgcore", "domain", "counters"):
            data.setdefault(k, {})
        return cls(data)

    # ----------------------------------------------------------------- lookups
    @property
    def entries(self) -> dict:
        return self.data["entries"]

    def get(self, original: str) -> dict | None:
        return self.entries.get(norm(original))

    def _next(self, key: str) -> int:
        c = self.data["counters"]
        c[key] = c.get(key, 0) + 1
        return c[key]

    def _used_replacements(self) -> set[str]:
        used = {norm(e["replacement"]) for e in self.entries.values()}
        for m in ("first", "last", "orgcore", "domain"):
            used |= {norm(v) for v in self.data[m].values()}
        return used

    def _originals(self) -> set[str]:
        s = set(self.entries.keys())
        for m in ("first", "last", "orgcore"):
            s |= set(self.data[m].keys())
        return s

    def _pick(self, pool: list[str], used: set[str]) -> str | None:
        blocked = used | self._originals()
        choices = [p for p in pool if norm(p) not in blocked]
        return _rng.choice(choices) if choices else None

    # ----------------------------------------------------------------- main API
    def replacement_for(self, original: str, category: str, style: str) -> dict:
        """Return (creating if needed) the vault entry for an original value."""
        key = norm(original)
        if key in self.entries:
            return self.entries[key]
        components: list[list[str]] = []
        repl = None
        if style == REALISTIC:
            try:
                repl, components = self._realistic(original, category)
            except Exception:
                repl = None
        if not repl:
            style = TOKEN
            prefix = CATEGORIES[category].token if category in CATEGORIES else category
            repl = f"[{prefix}_{self._next('tok:' + prefix)}]"
        entry = {"original": original, "category": category, "replacement": repl, "style": style,
                 "components": components, "created": datetime.now().isoformat(timespec="seconds")}
        self.entries[key] = entry
        self.dirty = True
        return entry

    def set_replacement(self, original: str, replacement: str):
        e = self.get(original)
        if e:
            e["replacement"] = replacement
            e["components"] = []
            e["style"] = "manual"
            self.dirty = True

    def remove(self, original: str):
        self.entries.pop(norm(original), None)
        self.dirty = True

    # ----------------------------------------------------------------- surrogates
    def _realistic(self, original: str, category: str):
        used = self._used_replacements()
        if category == "PERSON":
            return self._person(original, used)
        if category == "ORG":
            return self._org(original, used)
        if category == "EMAIL":
            return self._email(original), []
        if category == "PHONE":
            return self._phone(original), []
        if category == "URL":
            return self._url(original), []
        if category == "IP":
            return self._ip(original), []
        if category == "ADDRESS":
            return self._address(original), []
        if category == "LOCATION":
            c = self._pick(SURROGATE_CITY_LIST, used)
            return (c or None), []
        return None, []

    def _map_component(self, which: str, value: str, pool: list[str], used: set[str]) -> str:
        m = self.data[which]
        k = value.lower()
        if k not in m:
            pick = self._pick(pool, used)
            if not pick:
                pick = _rng.choice(pool) + "-" + _rng.choice(pool)
            m[k] = pick
            used.add(norm(pick))
        return m[k]

    def _person(self, original: str, used: set[str]):
        upper = original.isupper()
        comps: list[list[str]] = []
        if "," in original:  # Smith, John
            last, first = [x.strip() for x in original.split(",", 1)]
            first = first.split()[0] if first else first
            sl = self._map_component("last", last, SURROGATE_LAST, used)
            sf = self._map_component("first", first, SURROGATE_FIRST, used)
            out = f"{sl}, {sf}"
            comps = [[last, sl], [first, sf]]
        else:
            toks = original.split()
            if len(toks) == 1:
                t = toks[0]
                which, pool = ("first", SURROGATE_FIRST) if t.lower() in FIRST_NAMES else ("last", SURROGATE_LAST)
                s = self._map_component(which, t, pool, used)
                out = s
                comps = [[t, s]]
            else:
                first, last, middle = toks[0], toks[-1], toks[1:-1]
                sf = self._map_component("first", first, SURROGATE_FIRST, used)
                sl = self._map_component("last", last, SURROGATE_LAST, used)
                mids = []
                for mtok in middle:
                    if re.fullmatch(r"[A-Za-z]\.?", mtok):
                        mids.append(_rng.choice("ABCDEFGHJKLMNPRSTW") + ".")
                    else:
                        mids.append(self._map_component("first", mtok, SURROGATE_FIRST, used))
                        comps.append([mtok, mids[-1]])
                out = " ".join([sf] + mids + [sl])
                comps = [[first, sf], [last, sl]] + comps
        if upper:
            out = out.upper()
            comps = [[o.upper(), r.upper()] for o, r in comps]
        # components that are ordinary words are not safe to replace on their own
        comps = [[o, r] for o, r in comps
                 if len(o) > 2 and o.lower() not in COMMON_WORDS and o.lower() not in AMBIGUOUS_FIRST]
        return out, comps

    def _org(self, original: str, used: set[str]):
        words = original.replace(",", "").split()
        suffix = []
        while words and words[-1].rstrip(".") in [s.rstrip(".") for s in ORG_SUFFIXES]:
            suffix.insert(0, words.pop())
        core = " ".join(words) if words else original
        k = core.lower()
        if k not in self.data["orgcore"]:
            pick = self._pick(SURROGATE_ORG_CORE, used) or f"Company{self._next('orgfallback')}"
            self.data["orgcore"][k] = pick
        sc = self.data["orgcore"][k]
        out = " ".join([sc] + suffix) if suffix else sc
        comps = []
        if suffix and len(core) > 2 and core.lower() not in COMMON_WORDS:
            comps.append([core, sc])
        if len(words) > 1 and len(words[0]) > 3 and words[0].lower() not in COMMON_WORDS:
            comps.append([words[0], sc])
        if original.isupper():
            out = out.upper()
        return out, comps

    def _domain(self, domain: str) -> str:
        d = domain.lower()
        if d.startswith("www."):
            d = d[4:]
        dm = self.data["domain"]
        if d not in dm:
            stem = d.split(".")[0]
            core = self.data["orgcore"].get(stem)
            if not core:
                for oc, sur in self.data["orgcore"].items():
                    if oc.replace(" ", "").lower() == stem or oc.split()[0] == stem:
                        core = sur
                        break
            if not core:
                core = self._pick(SURROGATE_ORG_CORE, self._used_replacements()) or f"site{self._next('dom')}"
            cand = f"{core.lower().replace(' ', '')}.example"
            while cand in dm.values():
                cand = f"{core.lower()}{self._next('dom')}.example"
            dm[d] = cand
        return dm[d]

    def _email(self, original: str) -> str:
        local, _, domain = original.partition("@")
        parts = re.split(r"[._-]", local)
        sur_parts = []
        for p in parts:
            pl = p.lower()
            if pl in self.data["first"]:
                sur_parts.append(self.data["first"][pl].lower())
            elif pl in self.data["last"]:
                sur_parts.append(self.data["last"][pl].lower())
            else:
                sur_parts = []
                break
        new_local = ".".join(sur_parts) if sur_parts else f"user{self._next('email')}"
        return f"{new_local}@{self._domain(domain)}"

    def _phone(self, original: str) -> str:
        n = self._next("phone") - 1
        area = AREA_CODES[(n // 100) % len(AREA_CODES)]
        line = f"01{n % 100:02d}"
        core = f"({area}) 555-{line}"
        return ("+1 " + core) if original.strip().startswith("+") else core

    def _url(self, original: str) -> str:
        u = original if "://" in original else "http://" + original
        parts = urlsplit(u)
        host = self._domain(parts.hostname or original)
        if "://" not in original and not original.lower().startswith("www."):
            return host  # bare domain
        path = ""
        if parts.path and parts.path not in ("/", ""):
            path = f"/page-{self._next('urlpath')}"
        scheme = parts.scheme if "://" in original else ""
        prefix = f"{scheme}://" if scheme else ""
        www = "www." if (parts.hostname or "").startswith("www.") else ""
        return f"{prefix}{www}{host}{path}"

    def _ip(self, original: str) -> str:
        if re.fullmatch(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", original):
            n = self._next("mac")
            return f"00:00:5E:00:53:{n % 256:02X}"
        if ":" in original:
            return f"2001:db8::{self._next('ipv6'):x}"
        cidr = ""
        if "/" in original:
            original, cidr = original.split("/", 1)
            cidr = "/" + cidr
        n = self._next("ipv4")
        nets = ["192.0.2", "198.51.100", "203.0.113"]
        return f"{nets[(n - 1) // 254 % 3]}.{(n - 1) % 254 + 1}{cidr}"

    def _address(self, original: str) -> str:
        if re.match(r"(?i)P\.?\s?O\.?\s+Box", original):
            return f"PO Box {_rng.randint(1000, 9899)}"
        m = re.search(r",\s*([A-Z]{2})\s+\d{5}", original)
        if m:
            city = self._pick(SURROGATE_CITY_LIST, self._used_replacements()) or "Ashbury"
            return f"{city}, {_rng.choice(US_STATE_CODES)} {_rng.randint(10000, 99899)}"
        if re.match(r"\d", original):
            num = _rng.randint(10, 9899)
            street = f"{num} {_rng.choice(SURROGATE_STREETS)} {_rng.choice(STREET_SUFFIXES)}"
            if re.search(r"(?i)\b(suite|ste|apt|apartment|unit|floor|fl|room|rm|#)\b", original):
                street += f", Suite {_rng.randint(100, 899)}"
            return street
        if re.fullmatch(r"\d{5}(?:-\d{4})?", original.strip()):
            return f"{_rng.randint(10000, 99899)}"
        return None

    # ----------------------------------------------------------------- pairs
    def forward_pairs(self, keys: set[str] | None = None) -> list[tuple[str, str, bool]]:
        """(find, replace, case_sensitive) for sanitizing."""
        pairs = []
        for k, e in self.entries.items():
            if keys is not None and k not in keys:
                continue
            pairs.append((e["original"], e["replacement"], False))
            for o, r in e.get("components", []):
                pairs.append((o, r, True))
        return pairs

    def reverse_pairs(self) -> list[tuple[str, str, bool]]:
        """(find, replace, case_sensitive) for restoring an AI response."""
        pairs = []
        for e in self.entries.values():
            rep, orig = e["replacement"], e["original"]
            pairs.append((rep, orig, False))
            if rep.startswith("[") and rep.endswith("]"):
                pairs.append((rep[1:-1], orig, False))          # AI dropped the brackets
                pairs.append((rep[1:-1].replace("_", " "), orig, False))  # "PERSON 3"
            for o, r in e.get("components", []):
                pairs.append((r, o, True))
        for orig, sur in self.data["domain"].items():
            pairs.append((sur, orig, False))
        return pairs


def _fernet(password: str, salt: bytes):
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8"))))
