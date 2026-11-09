"""Catalogue of sensitive-information categories ЯedactR knows about."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    description: str
    token: str  # prefix used in token-style replacements, e.g. [PERSON_3]
    can_be_realistic: bool  # whether a realistic fictional surrogate can be generated


CATEGORIES: dict[str, Category] = {c.key: c for c in [
    Category("PERSON", "Person names", "First / last / full names of people", "PERSON", True),
    Category("EMAIL", "Email addresses", "Any email address", "EMAIL", True),
    Category("PHONE", "Phone numbers", "Phone / fax / mobile numbers", "PHONE", True),
    Category("ADDRESS", "Street addresses", "Street addresses and ZIP / postal codes", "ADDRESS", True),
    Category("SSN", "SSN / National ID", "US Social Security numbers, national ID, passport and tax numbers", "NATIONAL_ID", False),
    Category("CREDIT_CARD", "Payment cards", "Credit / debit card numbers (Luhn validated)", "CARD", False),
    Category("SECRET", "Passwords & keys", "Passwords, API keys, access tokens, private keys, connection strings", "SECRET", False),
    Category("DOB", "Dates of birth", "Dates that are labelled as a birth date", "DOB", False),
    Category("ORG", "Organisations", "Company / client / vendor / institution names", "ORG", True),
    Category("LOCATION", "Locations", "Cities, states, countries and sites mentioned as places", "LOCATION", True),
    Category("URL", "Web addresses", "URLs and domain names", "URL", True),
    Category("IP", "IP / MAC addresses", "IPv4, IPv6 and MAC addresses", "IP", True),
    Category("FINANCIAL", "Bank accounts", "IBAN, SWIFT/BIC, routing and account numbers", "ACCOUNT", False),
    Category("ID", "Internal IDs", "Employee, customer, invoice, order, case and ticket identifiers", "ID", False),
    Category("CUSTOM", "Custom terms", "Your own list of client names, project code names, products ...", "TERM", False),
    Category("MONEY", "Money amounts", "Currency amounts such as $1.2M, EUR 4,500", "AMOUNT", False),
    Category("DATE", "All dates", "Every calendar date", "DATE", False),
    Category("PERCENT", "Percentages", "Percent figures, e.g. 12.5%", "PCT", False),
    Category("NUMBER", "All other numbers", "Any remaining number with 2+ digits", "NUM", False),
    Category("PROPER_NOUN", "Other proper nouns", "Remaining capitalised names (products, projects, places)", "NAME", False),
    Category("PATH", "File paths", "Windows / Unix file paths and network shares", "PATH", False),
]}

CATEGORY_ORDER = list(CATEGORIES.keys())
