"""Rule-based detection of sensitive information.

Everything runs locally with regular expressions, checksums, dictionaries and
context clues - no network, no cloud model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .wordlists import (AMBIGUOUS_FIRST, CITIES, COMMON_WORDS, COUNTRIES, FIRST_NAMES, HONORIFICS,
                        ORG_SUFFIXES, US_STATE_CODES, US_STATES)


@dataclass
class Detection:
    start: int
    end: int
    text: str
    category: str
    rule: str
    priority: int = 50


# Higher priority wins when two detections overlap
PRIORITY = {
    "SECRET": 100, "CUSTOM": 95, "EMAIL": 90, "URL": 85, "CREDIT_CARD": 84, "FINANCIAL": 83, "SSN": 82,
    "IP": 80, "DOB": 79, "PATH": 78, "PHONE": 75, "ID": 72, "ADDRESS": 70, "ORG": 65, "PERSON": 60,
    "MONEY": 55, "DATE": 54, "PERCENT": 53, "LOCATION": 50, "PROPER_NOUN": 20, "NUMBER": 10,
}

CAP = r"[A-Z][a-zA-Z'\u00C0-\u017F]+(?:-[A-Z][a-zA-Z'\u00C0-\u017F]+)?"
MONTHS = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
          r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
DATE_RX = (
    r"(?:\d{4}-\d{1,2}-\d{1,2}"                                  # 2024-01-31
    r"|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}"                          # 01/31/2024, 31.01.24
    r"|\d{1,2}(?:st|nd|rd|th)?\s+" + MONTHS + r"\.?,?\s+\d{4}"     # 31 January 2024
    r"|" + MONTHS + r"\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"     # January 31, 2024
    r"|" + MONTHS + r"\.?\s+\d{4})"                                # January 2024
)


def _c(p, flags=0):
    return re.compile(p, flags)


# (category, rule name, compiled regex, capture group)
PATTERNS: list[tuple[str, str, re.Pattern, int]] = [
    # ---- secrets ------------------------------------------------------------------
    ("SECRET", "private-key", _c(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), 0),
    ("SECRET", "aws-key", _c(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("SECRET", "api-key", _c(r"\b(?:sk|pk|rk)[-_](?:live|test|proj|ant)?[-_]?[A-Za-z0-9_-]{16,}\b"), 0),
    ("SECRET", "github-token", _c(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), 0),
    ("SECRET", "slack-token", _c(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), 0),
    ("SECRET", "google-key", _c(r"\bAIza[0-9A-Za-z_-]{35}\b"), 0),
    ("SECRET", "jwt", _c(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), 0),
    ("SECRET", "labelled-secret", _c(
        r"(?i)\b(?:password|passwd|pwd|passcode|pin|secret|api[ _-]?key|access[ _-]?key|secret[ _-]?key|"
        r"client[ _-]?secret|auth[ _-]?token|access[ _-]?token|token)\s*(?:is|=|:)\s*[\"']?([^\s\"';,]{4,})"), 1),
    ("SECRET", "conn-string", _c(r"(?i)\b(?:password|pwd)=([^;\s]+)"), 1),
    # ---- contact ------------------------------------------------------------------
    ("EMAIL", "email", _c(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"), 0),
    ("URL", "url", _c(r"\b(?:https?://|ftp://|www\.)[^\s<>\"'\])]+[^\s<>\"'\]).,;:!?]"), 0),
    ("URL", "domain", _c(r"(?<![@\w.-])(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|gov|edu|biz|info|us|uk|ca|de|fr|"
                         r"au|in|pk|ae|sa|ai|app|dev|cloud|tech|eu|me)\b(?![@\w-])", re.I), 0),
    ("PHONE", "phone", _c(
        r"(?<![\w+])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)\s?|\d{2,4}[\s.-])\d{3,4}[\s.-]\d{3,5}"
        r"(?:\s?(?:x|ext\.?|extension)\s?\d{1,5})?(?![\w-])"), 0),
    ("PHONE", "phone-intl", _c(r"(?<![\w+])\+\d{1,3}(?:[\s.-]?\d{2,5}){2,5}(?!\w)"), 0),
    ("PHONE", "labelled-phone", _c(r"(?i)\b(?:tel|phone|mobile|mob|cell|fax|ph)\.?\s*(?:no\.?|number|#)?\s*[:#]?\s*"
                                   r"(\+?\d[\d\s().-]{6,18}\d)"), 1),
    # ---- identifiers --------------------------------------------------------------
    ("SSN", "ssn", _c(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"), 0),
    ("SSN", "labelled-id", _c(
        r"(?i)\b(?:ssn|social security(?: number| no\.?)?|passport|national id|nic|cnic|tax id|tin|ein|itin|nino|"
        r"sin|aadhaar|driver'?s? licen[cs]e|dl)\s*(?:no\.?|number|#|num)?\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{4,19})"), 1),
    ("CREDIT_CARD", "card", _c(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), 0),
    ("FINANCIAL", "iban", _c(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?\b"), 0),
    ("FINANCIAL", "labelled-account", _c(
        r"(?i)\b(?:account|acct|a/c|routing|aba|swift|bic|sort code|iban|bank account)\s*"
        r"(?:no\.?|number|#|num|code)?\s*[:#]?\s*(\d[\d -]{3,30}\d|[A-Z]{2}\d{2}[A-Z0-9]{8,30}|(?-i:[A-Z0-9]{8,11}))"), 1),
    ("IP", "ipv4", _c(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:/\d{1,2})?\b"), 0),
    ("IP", "ipv6", _c(r"\b(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}\b"), 0),
    ("IP", "mac", _c(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"), 0),
    ("ID", "labelled-id", _c(
        r"(?i)\b(?:employee|emp|staff|customer|cust|client|member|patient|mrn|invoice|inv|order|po|purchase order|"
        r"case|ticket|claim|policy|contract|reference|ref|user|student|badge|vendor|supplier|account|loan|"
        r"application|transaction|txn|tracking|serial|license|licence|asset|project)\s*"
        r"(?:id|no\.?|number|#|num|code)\s*[:#]?\s*([A-Z0-9][A-Z0-9_/.-]{2,24})"), 1),
    ("ID", "code-id", _c(r"\b[A-Z]{2,6}[-_]\d{2,}(?:[-_][A-Z0-9]+)*\b"), 0),
    ("DOB", "dob", _c(r"(?i)\b(?:dob|d\.o\.b\.?|date of birth|birth\s?date|birthday|born(?: on)?)\s*[:\-]?\s*(" + DATE_RX + ")"), 1),
    # ---- addresses ----------------------------------------------------------------
    ("ADDRESS", "street", _c(
        r"\b\d{1,6}[A-Z]?[ \t]+(?:[NSEW]\.?[ \t]+)?(?:" + CAP + r"[ \t]+){1,4}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|"
        r"Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter|Parkway|Pkwy|Circle|Cir|Highway|Hwy|Square|Sq|Trail|"
        r"Trl|Close|Crescent|Cres)\.?(?:,?\s+(?:Suite|Ste|Apt|Apartment|Unit|Floor|Fl|Room|Rm|#)\.?\s*[A-Za-z0-9-]+)?"), 0),
    ("ADDRESS", "po-box", _c(r"(?i)\bP\.?\s?O\.?\s+Box\s+\d+\b"), 0),
    ("ADDRESS", "city-state-zip", _c(
        r"\b(?:" + CAP + r"[ \t]){0,2}" + CAP + r",[ \t]*(?:" + "|".join(US_STATE_CODES) + r")\s+\d{5}(?:-\d{4})?\b"), 0),
    ("ADDRESS", "uk-postcode", _c(r"\b(?:[A-Z]{1,2}\d[A-Z\d]?)\s+\d[A-Z]{2}\b"), 0),
    ("ADDRESS", "labelled-zip", _c(r"(?i)\b(?:zip|zip code|postal code|postcode)\s*[:#]?\s*(\d{5}(?:-\d{4})?|[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})"), 1),
    # ---- paths ----------------------------------------------------------------------
    ("PATH", "win-path", _c(r"(?:\b[A-Za-z]:\\|\\\\[\w.$-]+\\)(?:[^\\/:*?\"<>|\r\n\t]+\\)*[^\\/:*?\"<>|\r\n\t ]*"), 0),
    ("PATH", "unix-path", _c(r"(?<![\w:/.])(?:~|/(?:home|Users|var|etc|opt|srv|mnt|usr|tmp|data))(?:/[\w.@-]+)+"), 0),
    # ---- numbers ----------------------------------------------------------------
    ("MONEY", "money", _c(
        r"(?:[$\u20ac\u00a3\u00a5\u20b9]|\b(?:USD|EUR|GBP|CAD|AUD|INR|PKR|AED|SAR|JPY|CHF|CNY|Rs\.?)\s?)\s?"
        r"\d[\d,]*(?:\.\d+)?(?:\s?(?:k|K|m|M|MM|bn|BN|B|million|billion|thousand|trillion)\b)?"), 0),
    ("MONEY", "money-suffix", _c(
        r"\b\d[\d,]*(?:\.\d+)?\s?(?:million|billion|thousand)?\s?(?:USD|EUR|GBP|dollars|euros|pounds|rupees)\b", re.I), 0),
    ("DATE", "date", _c(r"\b" + DATE_RX + r"\b"), 0),
    ("PERCENT", "percent", _c(r"(?<![\w.])[-+]?\d+(?:\.\d+)?\s?%"), 0),
    ("NUMBER", "number", _c(r"(?<![\w.])\d[\d,.]*\d(?![\w])"), 0),
]

# ---------------------------------------------------------------------------- names
_HON = r"(?:" + "|".join(HONORIFICS) + r")\.?"
NAME_TOKEN = CAP
_name_seq = _c(r"(?<![\w@.])(" + NAME_TOKEN + r")((?:[ \t\u00A0]+(?:[A-Z]\.|" + NAME_TOKEN + r")){1,3})")
_upper_seq = _c(r"(?<![\w@.])([A-Z]{2,})((?:[ \t\u00A0]+[A-Z]{2,}){1,2})(?![\w])")
_honorific = _c(r"\b" + _HON + r"[ \t\u00A0]+((?:[A-Z]\.[ \t]?)?" + NAME_TOKEN + r"(?:[ \t\u00A0]+" + NAME_TOKEN + r"){0,2})")
_label_name = _c(
    r"(?im)\b(?:name|full name|employee(?: name)?|contact(?: person)?|attn|attention|prepared by|approved by|"
    r"reviewed by|submitted by|author|signed by|manager|owner|assignee|reporter|customer name|client name|"
    r"patient|tenant|landlord|recipient|sender|requester|requested by|from|to|cc|bcc|witness|beneficiary|"
    r"account holder|cardholder|guarantor|director|ceo|cfo|president)\s*[:\-]\s*(" + NAME_TOKEN +
    r"(?:[ \t\u00A0]+(?:[A-Z]\.[ \t]?)?" + NAME_TOKEN + r"){0,3})")
_salutation = _c(r"\b(?:Dear|Hi|Hello|Hey|Thanks|Thank you|Regards|Sincerely|Cheers|Best),?[ \t\u00A0]+(" + NAME_TOKEN +
                 r"(?:[ \t\u00A0]+" + NAME_TOKEN + r")?)\b")
_last_first = _c(r"(?<![\w@.])(" + NAME_TOKEN + r"),\s(" + NAME_TOKEN + r")(?![\w])")
_single_first = _c(r"(?<![\w@.])(" + NAME_TOKEN + r")(?![\w@])")
_email_name = _c(r"\b([a-z]+)[._]([a-z]+)@", re.I)

_org = _c(r"(?<![\w])((?:(?:[A-Z][\w&'.-]*|&)[ \t]+){0,4}[A-Z][\w&'.-]*,?[ \t\u00A0]+(?:" +
          "|".join(re.escape(s) for s in ORG_SUFFIXES) + r"))(?![\w])")
# Brand-shaped names with no "Inc/LLC": GlobexCorp, PayPal, McKinsey, X-CORP, AT&T-style tokens
_brand = _c(r"(?<![\w@./\\-])([A-Z][a-z]+[A-Z][A-Za-z]*|[A-Z]{1,6}(?:[&-][A-Z]{2,})+|[A-Z]{1,6}&[A-Z]{1,6}(?=\s+[A-Z]))(?![\w@-]|\.[a-z])")
# well-known products / platforms / words that look like brands but are not confidential
BRAND_ALLOW = {w.lower() for w in """
PowerPoint SharePoint OneDrive OneNote JavaScript TypeScript LinkedIn YouTube GitHub GitLab WordPress PayPal
MacBook iPhone iPad macOS iOS ChatGPT OpenAI DeepMind PhD McAfee DevOps DevSecOps FinOps SecOps MySQL
PostgreSQL NoSQL GraphQL OAuth SaaS PaaS IaaS FedEx WhatsApp TikTok FaceTime AirDrop DocuSign DropBox
QuickBooks WiFi Wi-Fi eBay BitLocker CrowdStrike PowerShell VMware VirtualBox NetBIOS DynamoDB MongoDB
BigQuery RedHat FreeBSD OpenSSL OpenVPN WireGuard ServiceNow SalesForce HubSpot MailChimp ZoomInfo
JetBrains IntelliJ PyCharm AutoCAD SketchUp PhotoShop InDesign McDonalds KPIs SLAs APIs URLs PDFs FAQs
T-SQL PL-SQL UTF COVID-19 Q&A R&D P&L M&A B&W A&E S&P AT&T-
""".split()}
_loc_words = sorted(US_STATES + COUNTRIES + CITIES, key=len, reverse=True)
_location = _c(r"\b(?:" + "|".join(re.escape(w) for w in _loc_words) + r")\b")
_proper = _c(r"(?<![\w@./\\-])([A-Z][a-zA-Z0-9]*(?:[-'][A-Za-z0-9]+)*(?:[ \t\u00A0]+[A-Z][a-zA-Z0-9]*(?:[-'][A-Za-z0-9]+)*)*)")
_sentence_start = _c(r"(?:^|[.!?:;\n\r\t\u2022\-*>\"(]\s*|\n\s*)$")


def _is_common(word: str) -> bool:
    return word.lower().strip(".,'") in COMMON_WORDS


def luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if len(d) < 13 or len(d) > 19 or len(set(d)) == 1:
        return False
    total = 0
    for i, n in enumerate(reversed(d)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _trim_name(tokens: list[str]) -> list[str]:
    """Drop trailing tokens that are ordinary words (e.g. 'John Smith Report' -> John Smith)."""
    while tokens and (_is_common(tokens[-1]) or tokens[-1] in ORG_SUFFIXES):
        tokens = tokens[:-1]
    return tokens


class Detector:
    def __init__(self, categories: set[str], custom_terms: list[tuple[str, str]] | None = None,
                 custom_patterns: list[tuple[str, re.Pattern]] | None = None, allow_list: list[str] | None = None):
        self.categories = set(categories)
        self.custom_terms = custom_terms or []
        self.custom_patterns = custom_patterns or []
        self.allow = {a.strip().lower() for a in (allow_list or []) if a.strip()}

    # ------------------------------------------------------------------ public
    def detect(self, text: str) -> list[Detection]:
        if not text or not text.strip():
            return []
        found: list[Detection] = []
        want = self.categories

        # custom terms are always looked for when the user listed them
        for term, cat in self.custom_terms:
            for m in re.finditer(r"(?<!\w)" + re.escape(term).replace(r"\ ", r"\s+") + r"(?!\w)", text, re.I):
                found.append(Detection(m.start(), m.end(), m.group(0), cat, "custom-term", 95))
        for label, rx in self.custom_patterns:
            for m in rx.finditer(text):
                g = 1 if rx.groups else 0
                if m.group(g):
                    found.append(Detection(m.start(g), m.end(g), m.group(g), "CUSTOM", f"pattern:{label}", 96))

        for cat, rule, rx, grp in PATTERNS:
            if cat not in want:
                continue
            for m in rx.finditer(text):
                s, e = m.span(grp)
                val = m.group(grp)
                if not val:
                    continue
                val, e = self._rstrip(val, s)
                if not self._validate(cat, rule, val):
                    continue
                found.append(Detection(s, e, val, cat, rule, PRIORITY[cat]))

        if "PERSON" in want:
            found += self._persons(text)
        if "ORG" in want:
            for m in _org.finditer(text):
                val = self._clean_org(m.group(1))
                if val:
                    s = m.start(1) + m.group(1).find(val)
                    found.append(Detection(s, s + len(val), val, "ORG", "org-suffix", PRIORITY["ORG"]))
            for m in _brand.finditer(text):
                val = m.group(1)
                if val.lower() in BRAND_ALLOW or val.lower() in self.allow or _is_common(val):
                    continue
                found.append(Detection(m.start(1), m.end(1), val, "ORG", "brand-name", PRIORITY["ORG"] - 2))
        if "LOCATION" in want:
            for m in _location.finditer(text):
                found.append(Detection(m.start(), m.end(), m.group(0), "LOCATION", "gazetteer", PRIORITY["LOCATION"]))
        if "PROPER_NOUN" in want:
            found += self._proper_nouns(text)

        return self._resolve(found)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _rstrip(val: str, start: int):
        v = val.rstrip(" .,;:-")
        return v, start + len(v)

    def _validate(self, cat, rule, val) -> bool:
        if val.strip().lower() in self.allow:
            return False
        if cat == "CREDIT_CARD":
            return luhn_ok(val)
        if cat == "PHONE":
            digits = sum(c.isdigit() for c in val)
            if digits < 7 or digits > 15:
                return False
            if re.fullmatch(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", val) or re.fullmatch(r"\d{1,2}[-./]\d{1,2}[-./]\d{2,4}", val):
                return False
            return True
        if cat in ("ID", "FINANCIAL") and rule.startswith("labelled") or rule == "labelled-id":
            return any(ch.isdigit() for ch in val) and not _is_common(val)
        if rule == "iban":
            return len(val.replace(" ", "")) >= 15
        if rule == "domain":
            return not re.fullmatch(r"(?:e\.g|i\.e|etc)\.\w+", val, re.I) and "." in val and not val[0].isdigit()
        if rule == "uk-postcode":
            return True
        if cat == "NUMBER":
            return sum(c.isdigit() for c in val) >= 2
        return True

    def _persons(self, text: str) -> list[Detection]:
        out: list[Detection] = []
        pr = PRIORITY["PERSON"]

        def add(s, e, rule, boost=0):
            val = text[s:e]
            if val.lower() in self.allow or len(val) < 2:
                return
            out.append(Detection(s, e, val, "PERSON", rule, pr + boost))

        # Firstname Lastname (first name from dictionary)
        for m in _name_seq.finditer(text):
            first = m.group(1)
            rest = m.group(2).split()
            if first.lower() not in FIRST_NAMES:
                continue
            if _is_common(first) and first.lower() not in FIRST_NAMES:
                continue
            tokens = _trim_name([first] + rest)
            if len(tokens) < 2:
                continue
            if any(t.lower() in COMMON_WORDS and len(t) > 2 for t in tokens[1:]):
                # e.g. "Will Report" - second word is ordinary
                tokens = [first] + [t for t in tokens[1:2] if not _is_common(t)]
                if len(tokens) < 2:
                    continue
            s = m.start(1)
            add(s, self._span_end(text, s, tokens), "first-last")

        # ALL CAPS names in sheets / headers: JOHN SMITH
        for m in _upper_seq.finditer(text):
            first = m.group(1)
            if first.lower() in FIRST_NAMES and first.lower() not in AMBIGUOUS_FIRST:
                rest = [t for t in m.group(2).split() if not _is_common(t)]
                if rest:
                    e = self._span_end(text, m.start(1), [first] + rest[:2])
                    add(m.start(1), e, "caps-name")

        # Smith, John
        for m in _last_first.finditer(text):
            if m.group(2).lower() in FIRST_NAMES and not _is_common(m.group(1)) and m.group(1).lower() not in FIRST_NAMES:
                add(m.start(1), m.end(2), "last-first")

        # Mr. / Dr. ...
        for m in _honorific.finditer(text):
            tokens = _trim_name(m.group(1).split())
            if tokens:
                add(m.start(1), self._span_end(text, m.start(1), tokens), "honorific", 5)

        # Name: Jane Doe / Prepared by: ...
        for m in _label_name.finditer(text):
            tokens = _trim_name(m.group(1).split())
            if tokens and not any(t in ORG_SUFFIXES for t in tokens) and not all(_is_common(t) for t in tokens):
                if len(tokens) == 1 and tokens[0].lower() not in FIRST_NAMES:
                    continue
                add(m.start(1), self._span_end(text, m.start(1), tokens), "label-context", 3)

        # Dear Sarah,
        for m in _salutation.finditer(text):
            tokens = _trim_name(m.group(1).split())
            if tokens and not _is_common(tokens[0]):
                add(m.start(1), self._span_end(text, m.start(1), tokens), "salutation", 2)

        # john.smith@company.com -> also hunt the name "John Smith" elsewhere (handled by vault components)
        for m in _email_name.finditer(text):
            f, l = m.group(1), m.group(2)
            if f.lower() in FIRST_NAMES and len(l) > 2 and not _is_common(l):
                rx = re.compile(r"(?<!\w)" + re.escape(f.capitalize()) + r"\s+" + re.escape(l.capitalize()) + r"(?!\w)")
                for mm in rx.finditer(text):
                    add(mm.start(), mm.end(), "email-derived")

        # stand-alone first names (non ambiguous) e.g. "Sarah approved the budget"
        for m in _single_first.finditer(text):
            w = m.group(1)
            lw = w.lower()
            if lw in FIRST_NAMES and lw not in AMBIGUOUS_FIRST and lw not in COMMON_WORDS:
                add(m.start(1), m.end(1), "first-name", -15)
        return out

    @staticmethod
    def _span_end(text: str, start: int, tokens: list[str]) -> int:
        pos = start
        for i, t in enumerate(tokens):
            idx = text.find(t, pos)
            if idx < 0:
                break
            pos = idx + len(t)
        return pos

    @staticmethod
    def _clean_org(val: str) -> str | None:
        words = val.replace(",", " ,").split()
        # drop leading ordinary words ("The", "With", "Report from" ...)
        while words and (words[0].lower() in COMMON_WORDS or words[0] in ("&", "and", "of", ",")) and \
                words[0] not in ORG_SUFFIXES:
            words = words[1:]
        if len(words) < 2:
            return None
        out = " ".join(words).replace(" ,", ",")
        core = [w for w in words if w not in ORG_SUFFIXES and w != ","]
        if not core or all(w.lower() in COMMON_WORDS for w in core):
            return None
        return out

    def _proper_nouns(self, text: str) -> list[Detection]:
        out = []
        for m in _proper.finditer(text):
            words = m.group(1).split()
            s = m.start(1)
            # skip the first word if it begins a sentence / line
            if _sentence_start.search(text[max(0, s - 4):s]) or s == 0:
                if len(words) == 1:
                    continue
            keep = [w for w in words if not _is_common(w) and len(w) > 1]
            if not keep:
                continue
            for w in words:
                if _is_common(w) or len(w) <= 1:
                    continue
                idx = text.find(w, s)
                if idx < 0:
                    continue
                if (idx == m.start(1)) and (idx == 0 or _sentence_start.search(text[max(0, idx - 4):idx])):
                    # first word of a sentence - only flag if it is not a dictionary word
                    if w.lower() in COMMON_WORDS:
                        continue
                out.append(Detection(idx, idx + len(w), w, "PROPER_NOUN", "capitalised", PRIORITY["PROPER_NOUN"]))
                s = idx + len(w)
        return out

    @staticmethod
    def _resolve(found: list[Detection]) -> list[Detection]:
        """Keep the best non-overlapping detections (priority, then length)."""
        found.sort(key=lambda d: (-d.priority, -(d.end - d.start), d.start))
        taken: list[tuple[int, int]] = []
        result = []
        for d in found:
            if d.end <= d.start:
                continue
            if any(not (d.end <= a or d.start >= b) for a, b in taken):
                continue
            taken.append((d.start, d.end))
            result.append(d)
        result.sort(key=lambda d: d.start)
        return result


def parse_custom_terms(lines: list[str]) -> list[tuple[str, str]]:
    """Lines like 'Project Falcon' or 'Acme Corp => ORG'."""
    out = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" in line:
            term, cat = [x.strip() for x in line.split("=>", 1)]
            cat = cat.upper() or "CUSTOM"
        else:
            term, cat = line, "CUSTOM"
        if term:
            out.append((term, cat))
    return out


def parse_custom_patterns(lines: list[str]) -> tuple[list[tuple[str, re.Pattern]], list[str]]:
    """Lines like 'Project code = PRJ-\\d{4}'. Returns (patterns, errors)."""
    pats, errors = [], []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line and not line.startswith("="):
            label, rx = line.split("=", 1)
            label, rx = label.strip(), rx.strip()
        else:
            label, rx = "pattern", line
        try:
            pats.append((label or "pattern", re.compile(rx)))
        except re.error as exc:
            errors.append(f"{line!r}: {exc}")
    return pats, errors
