"""Sanitization levels (profiles).

Each level is cumulative: it contains everything the previous level removes,
plus more.  "Custom" lets the user pick any combination.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

from .categories import CATEGORIES, CATEGORY_ORDER

REALISTIC = "realistic"  # replace with believable fictional values (John Smith -> Daniel Brooks)
TOKEN = "token"          # replace with placeholders ([PERSON_3])


@dataclass
class Profile:
    key: str
    name: str
    tagline: str
    description: str
    categories: list[str]
    style: dict[str, str] = field(default_factory=dict)  # category -> REALISTIC / TOKEN
    strip_metadata: bool = False
    custom_terms: list[str] = field(default_factory=list)     # always redact (optionally "term => CATEGORY")
    allow_list: list[str] = field(default_factory=list)       # never redact
    custom_patterns: list[str] = field(default_factory=list)  # "Label = regex"

    def style_for(self, category: str) -> str:
        s = self.style.get(category)
        if s:
            return s
        cat = CATEGORIES.get(category)
        return REALISTIC if cat and cat.can_be_realistic else TOKEN

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def _all_realistic(cats):
    return {c: (REALISTIC if CATEGORIES[c].can_be_realistic else TOKEN) for c in cats}


L1 = ["PERSON"]
L2 = L1 + ["EMAIL", "PHONE", "ADDRESS", "SSN", "CREDIT_CARD", "SECRET", "DOB"]
L3 = L2 + ["ORG", "LOCATION", "URL", "IP", "FINANCIAL", "ID", "CUSTOM"]
L4 = L3 + ["MONEY", "DATE", "PERCENT", "PATH"]
L5 = L4 + ["NUMBER", "PROPER_NOUN"]

LEVELS: list[Profile] = [
    Profile(
        key="L1", name="Level 1 - Alias",
        tagline="People become fictional characters",
        description=("Replaces every person's name with a consistent fictional name "
                     "(John Smith -> Daniel Brooks). Everything else is left untouched. "
                     "Use for low-risk text where only identities matter."),
        categories=L1, style=_all_realistic(L1),
    ),
    Profile(
        key="L2", name="Level 2 - Private",
        tagline="Personal data (PII) removed",
        description=("Level 1 plus emails, phone numbers, street addresses, SSN / national IDs, "
                     "payment cards, dates of birth and any passwords or API keys. "
                     "Contact details are swapped for safe fictional ones (example.com, 555-01xx)."),
        categories=L2, style=_all_realistic(L2),
    ),
    Profile(
        key="L3", name="Level 3 - Confidential",
        tagline="Company & client identity hidden",
        description=("Level 2 plus organisation / client / vendor names, locations, web addresses, "
                     "IP addresses, bank account numbers, internal IDs (employee, invoice, case ...) and "
                     "your custom term list. Document metadata (author, company) is wiped."),
        categories=L3, style=_all_realistic(L3), strip_metadata=True,
    ),
    Profile(
        key="L4", name="Level 4 - Restricted",
        tagline="Financials, dates and paths masked",
        description=("Level 3 plus money amounts, all dates, percentages and file paths. "
                     "Names stay realistic so the AI can still reason naturally, but numbers and "
                     "dates become placeholders like [AMOUNT_2] and [DATE_5]."),
        categories=L4, style=_all_realistic(L4), strip_metadata=True,
    ),
    Profile(
        key="L5", name="Level 5 - Top Secret",
        tagline="Maximum masking - placeholders only",
        description=("Everything in Level 4 plus every remaining number and capitalised proper noun. "
                     "All values become neutral placeholders ([PERSON_1], [ORG_2], [NUM_7]) - "
                     "no realistic surrogates at all. Use for highly sensitive material."),
        categories=L5, style={c: TOKEN for c in L5}, strip_metadata=True,
    ),
]

LEVELS_BY_KEY = {p.key: p for p in LEVELS}


def default_custom_profile() -> Profile:
    base = LEVELS_BY_KEY["L3"]
    return Profile(
        key="CUSTOM", name="Custom",
        tagline="Your own combination",
        description="Choose exactly which categories to remove, how to replace them, and your own terms and patterns.",
        categories=list(base.categories), style=dict(base.style), strip_metadata=True,
    )


def ordered(cats: list[str]) -> list[str]:
    return [c for c in CATEGORY_ORDER if c in cats]
