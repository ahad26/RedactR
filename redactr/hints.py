"""Column/row header hints: in tables and spreadsheets the header tells us what
a cell contains even when the value itself looks harmless."""

import re

_EXCLUDE = re.compile(r"(?i)\b(product|project|file|item|task|department|dept|team|title|job|position|role|"
                      r"category|type|status|description|subject|course|module|program|plan|tier|sheet|tab|"
                      r"field|column|model|brand|service|stage|step|phase|unit)\b")

_RULES = [
    ("EMAIL", r"\be-?mail\b"),
    ("PHONE", r"\b(phone|mobile|cell|tel|telephone|fax|contact no|contact number)\b"),
    ("SSN", r"\b(ssn|social security|national id|passport|tax id|tin|nic|cnic|nino|sin|aadhaar|driver'?s? licen[cs]e)\b"),
    ("DOB", r"\b(dob|date of birth|birth ?date|birthday)\b"),
    ("CREDIT_CARD", r"\b(card number|card no|credit card|debit card|cc number|pan)\b"),
    ("FINANCIAL", r"\b(iban|account number|account no|acct|routing|swift|bic|sort code|bank account)\b"),
    ("ADDRESS", r"\b(address|street|addr|zip|postal|postcode|zip code)\b"),
    ("LOCATION", r"\b(city|town|country|state|province|county|location|site|office location|branch)\b"),
    ("ORG", r"\b(company|organi[sz]ation|org|vendor|supplier|employer|firm|bank|business|agency|institution|"
            r"carrier|insurer|partner|contractor|distributor|reseller|account name)\b"),
    ("ID", r"\b(employee id|emp id|emp no|staff id|customer id|client id|member id|patient id|mrn|invoice|"
           r"order id|order no|order number|ticket|case id|case no|claim|policy|contract no|reference|ref no|"
           r"user id|badge|po number|po no|id)\b"),
    ("MONEY", r"\b(salary|wage|pay|compensation|bonus|amount|price|cost|revenue|income|balance|payment|fee|"
              r"budget|spend|total|value|commission|invoice amount)\b"),
    ("PERSON", r"\b(name|full name|first name|last name|surname|given name|employee|staff|contact|customer|"
               r"client|patient|owner|manager|assignee|requester|approver|reviewer|author|rep|salesperson|"
               r"account manager|recruiter|candidate|applicant|student|member|username|user|supervisor|"
               r"lead|participant|attendee|tenant|beneficiary|insured|guarantor|signatory|director)\b"),
]
_RULES = [(c, re.compile(r, re.I)) for c, r in _RULES]


def header_category(header: str) -> str | None:
    h = (header or "").strip()
    if not h or len(h) > 40:
        return None
    for cat, rx in _RULES:
        if rx.search(h):
            if cat == "PERSON" and _EXCLUDE.search(h):
                return None
            if cat == "ID" and h.lower().strip() == "id":
                return "ID"
            return cat
    return None


def table_hints(rows: list[list[str]], location: str) -> list[tuple[str, str, str]]:
    """rows: list of cell texts. Use the first non-empty row as headers."""
    out = []
    header = None
    for r in rows:
        if header is None:
            if sum(1 for c in r if c and c.strip()) >= 2:
                header = [header_category(c) for c in r]
            continue
        for i, val in enumerate(r):
            if i < len(header) and header[i] and val and val.strip():
                v = val.strip()
                if header[i] == "MONEY" and not re.search(r"\d", v):
                    continue
                if len(v) <= 120:
                    out.append((v, header[i], location))
    return out
