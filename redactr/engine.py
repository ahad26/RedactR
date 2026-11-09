"""Core engine: scan text -> findings -> replacement plan -> apply / reverse."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .categories import CATEGORY_ORDER
from .detectors import Detection, Detector, parse_custom_patterns, parse_custom_terms
from .levels import Profile
from .vault import Vault, norm


# ======================================================================== Replacer
class Replacer:
    """Fast multi-string find/replace with word boundaries, flexible whitespace and
    case preservation.  Used both for sanitizing and for restoring."""

    def __init__(self, pairs: list[tuple[str, str, bool]]):
        self.lookup: dict[str, tuple[str, bool, str]] = {}
        for find, repl, cs in pairs:
            if not find or not find.strip():
                continue
            k = norm(find)
            if k not in self.lookup:
                self.lookup[k] = (repl, cs, find)
        alts = sorted(self.lookup.values(), key=lambda v: len(v[2]), reverse=True)
        if alts:
            body = "|".join(self._guarded(v[2]) for v in alts)
            self.rx = re.compile(body, re.IGNORECASE)
        else:
            self.rx = None
        self.counts: dict[str, int] = defaultdict(int)

    @staticmethod
    def _escape(s: str) -> str:
        return r"\s+".join(re.escape(p) for p in s.strip().split())

    @classmethod
    def _guarded(cls, s: str) -> str:
        """Word boundaries; numbers additionally must not continue as 1,200.50 / 3.14."""
        s = s.strip()
        pre = r"(?<!\w)(?<!\d[.,])" if s[:1].isdigit() else r"(?<!\w)"
        post = r"(?![\w]|[.,]\d)" if s[-1:].isdigit() else r"(?!\w)"
        return pre + cls._escape(s) + post

    def matches(self, text: str) -> list[tuple[int, int, str, str]]:
        """List of (start, end, replacement, normkey) for every hit in text."""
        if not self.rx or not text:
            return []
        out = []
        for m in self.rx.finditer(text):
            found = m.group(0)
            k = norm(found)
            item = self.lookup.get(k)
            if not item:
                continue
            repl, cs, original = item
            if cs and not (found == original or found == original.upper() or found == original.title()):
                continue
            if (found.isupper() and not original.isupper() and len(found) > 1
                    and not repl.startswith("[")):
                repl = repl.upper()
            elif found.islower() and not original.islower() and not repl.startswith("["):
                repl = repl.lower()   # e.g. the company name inside an email / web address
            out.append((m.start(), m.end(), repl, k))
        return out

    def sub(self, text: str) -> str:
        hits = self.matches(text)
        if not hits:
            return text
        parts, pos = [], 0
        for s, e, repl, k in hits:
            parts.append(text[pos:s])
            parts.append(repl)
            pos = e
            self.counts[k] += 1
        parts.append(text[pos:])
        return "".join(parts)

    def sub_segments(self, segments: list[str]) -> list[str]:
        """Replace across a list of adjacent text segments (e.g. Word runs) while
        keeping each segment's formatting.  A match that spans segments is written
        into the segment where it starts."""
        full = "".join(segments)
        hits = self.matches(full)
        if not hits:
            return segments
        owner = []
        for i, seg in enumerate(segments):
            owner.extend([i] * len(seg))
        out = [""] * len(segments)
        pos = 0
        for s, e, repl, k in hits:
            for j in range(pos, s):
                out[owner[j]] += full[j]
            out[owner[s]] += repl
            pos = e
            self.counts[k] += 1
        for j in range(pos, len(full)):
            out[owner[j]] += full[j]
        return out


# ======================================================================== Findings
@dataclass
class Finding:
    original: str
    category: str
    count: int = 0
    sources: set = field(default_factory=set)
    rules: set = field(default_factory=set)
    include: bool = True
    replacement: str = ""
    replaced: int = 0

    @property
    def key(self):
        return norm(self.original)


class Sanitizer:
    def __init__(self, profile: Profile, vault: Vault):
        self.profile = profile
        self.vault = vault
        pats, self.pattern_errors = parse_custom_patterns(profile.custom_patterns)
        terms = parse_custom_terms(profile.custom_terms)
        cats = set(profile.categories)
        if terms:
            cats.add("CUSTOM")
        self.detector = Detector(cats, terms, pats, profile.allow_list)
        self.allow = {a.strip().lower() for a in profile.allow_list if a.strip()}
        self.findings: dict[str, Finding] = {}
        self.aliases: dict[str, str] = {}  # norm(variant) -> canonical spelling (same fictional name)

    # ------------------------------------------------------------------ scanning
    def scan(self, text: str, source: str) -> list[Detection]:
        dets = self.detector.detect(text)
        for d in dets:
            self._add(d.text, d.category, source, d.rule)
        return dets

    def add_forced(self, value: str, category: str, source: str, rule: str = "column-header"):
        value = (value or "").strip()
        if len(value) < 2 or category not in self.profile.categories:
            return
        self._add(value, category, source, rule)

    # webmail / generic hosts that say nothing about the organisation
    _GENERIC_DOMAINS = {"gmail", "googlemail", "yahoo", "hotmail", "outlook", "live", "msn", "icloud", "me", "aol",
                        "proton", "protonmail", "gmx", "mail", "zoho", "yandex", "example", "google", "microsoft",
                        "office", "office365", "sharepoint", "onedrive", "dropbox", "box", "linkedin", "facebook",
                        "twitter", "x", "youtube", "zoom", "teams", "slack", "github", "amazonaws", "cloudfront",
                        "w3", "schemas", "openxmlformats", "purl", "adobe", "apple", "wikipedia"}
    _SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu", "ltd", "plc"}

    def derive_org_names(self, texts: list[tuple[str, str]]):
        """Company names hiding in plain sight: if any document mentions @globexcorp.com or initech-labs.io,
        then 'GlobexCorp' / 'INITECH-LABS' written anywhere is the organisation's name."""
        if "ORG" not in self.profile.categories:
            return
        stems = set()
        for f in list(self.findings.values()):
            if f.category not in ("EMAIL", "URL"):
                continue
            host = f.original.split("@", 1)[1] if "@" in f.original else re.sub(r"^[a-z]+://", "", f.original, flags=re.I)
            labels = [x for x in host.split("/")[0].lower().split(".") if x and x != "www"]
            if len(labels) < 2:
                continue
            labels = labels[:-1]  # drop TLD
            if len(labels) >= 2 and labels[-1] in self._SECOND_LEVEL:
                labels = labels[:-1]  # acme.co.uk
            stem = labels[-1]
            if len(re.sub(r"[^a-z0-9]", "", stem)) >= 3 and stem not in self._GENERIC_DOMAINS:
                stems.add(stem)
        for stem in stems:
            chars = [c for c in stem if c.isalnum()]
            rx = re.compile(r"(?<![\w@./-])" + r"[-\s.&]?".join(map(re.escape, chars)) + r"(?![\w-]|\.[a-z])", re.I)
            variants = []
            for src, text in texts:
                for m in rx.finditer(text):
                    val = m.group(0)
                    if any(c.isupper() for c in val) and norm(val) not in self.allow:  # 'apple' the fruit stays
                        self._add(val, "ORG", src, "email-domain")
                        variants.append(val)
            # spelling variants (INITECH-LABS / InitechLabs / Initech Labs) all get the same fictional name
            if variants:
                canon = max(variants, key=lambda v: (sum(c.isupper() for c in v) > 1 and not v.isupper(),
                                                     "-" in v or "&" in v, variants.count(v)))
                for v in set(variants):
                    if norm(v) != norm(canon):
                        self.aliases[norm(v)] = canon

    def add_manual(self, value: str, category: str):
        self._add(value, category, "manual", "manual")

    def _add(self, text, category, source, rule):
        if not text or norm(text) in self.allow:
            return
        k = norm(text)
        f = self.findings.get(k)
        if not f:
            f = self.findings[k] = Finding(text, category)
        f.count += 1
        f.sources.add(source)
        f.rules.add(rule)

    def sorted_findings(self) -> list[Finding]:
        order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
        return sorted(self.findings.values(), key=lambda f: (order.get(f.category, 99), f.original.lower()))

    # ------------------------------------------------------------------ planning
    def plan(self) -> Replacer:
        """Assign replacements (people first so emails can reuse their aliases) and
        build the replacer for this run."""
        prio = ["PERSON", "ORG", "LOCATION"]
        items = sorted(self.findings.values(),
                       key=lambda f: (prio.index(f.category) if f.category in prio else 9, -len(f.original)))
        keys = set()
        for f in items:
            if not f.include:
                continue
            canon = self.aliases.get(f.key)
            if canon and f.key not in self.vault.entries:
                c = self.vault.replacement_for(canon, f.category, self.profile.style_for(f.category))
                self.vault.entries[f.key] = {**c, "original": f.original, "components": [], "alias_of": canon}
                self.vault.dirty = True
            entry = self.vault.replacement_for(f.original, f.category, self.profile.style_for(f.category))
            f.replacement = entry["replacement"]
            keys.add(f.key)
        pairs = [p for p in self.vault.forward_pairs(keys) if norm(p[0]) not in self.allow]
        return Replacer(pairs)

    def collect_counts(self, replacer: Replacer):
        for k, n in replacer.counts.items():
            if k in self.findings:
                self.findings[k].replaced = n


class Restorer:
    def __init__(self, vault: Vault):
        self.vault = vault

    def new_replacer(self) -> Replacer:
        return Replacer(self.vault.reverse_pairs())

    def restore_text(self, text: str) -> tuple[str, dict]:
        r = self.new_replacer()
        out = r.sub(text)
        return out, dict(r.counts)
