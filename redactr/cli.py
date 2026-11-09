"""Command line interface (handy for batch jobs and scripting).

    python -m redactr.cli sanitize  --project P --level L3 file1.docx file2.pdf
    python -m redactr.cli restore   --project P --text "answer from AI"
    python -m redactr.cli restore   --project P --file answer.docx
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from . import APP_NAME, AUTHOR, AUTHOR_URL
from .pipeline import SanitizeJob, restore_file, restore_text
from .project import Project
from .vault import VaultError


def _ask(prompt: str, given: str | None) -> str | None:
    if given is not None:
        return given or None
    env = os.environ.get("REDACTR_PASSWORD")
    if env is not None:
        return env or None
    if not sys.stdin.isatty():
        return None
    return getpass.getpass(prompt) or None


def _open(folder: str, create: bool, password: str | None = None) -> Project:
    if not Project.is_project(folder):
        if not create:
            sys.exit(f"{folder} is not a {APP_NAME} project (use --create).")
        pw = _ask("New vault password (empty = none): ", password)
        return Project.create(folder, os.path.basename(folder), pw)
    pw = _ask("Vault password: ", password) if Project.needs_password(folder) else None
    try:
        return Project.open(folder, pw)
    except VaultError as exc:
        sys.exit(str(exc))


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
        except (AttributeError, ValueError):
            pass
    ap =argparse.ArgumentParser(prog="redactr", description=f"{APP_NAME} - local document sanitizer",
                                 epilog=f"Software by {AUTHOR} - {AUTHOR_URL}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sanitize", help="create sanitized copies")
    s.add_argument("files", nargs="+")
    s.add_argument("--project", required=True)
    s.add_argument("--create", action="store_true", help="create the project if missing")
    s.add_argument("--level", default="L3", choices=["L1", "L2", "L3", "L4", "L5", "CUSTOM"])
    s.add_argument("--no-ocr", action="store_true")
    s.add_argument("--password", help="vault password (or set REDACTR_PASSWORD; prompted if omitted)")
    r = sub.add_parser("restore", help="restore an AI answer")
    r.add_argument("--project", required=True)
    r.add_argument("--password", help="vault password (or set REDACTR_PASSWORD)")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file")
    args = ap.parse_args(argv)

    if args.cmd == "sanitize":
        p = _open(args.project, args.create, args.password)
        job = SanitizeJob(p, p.profile(args.level), [os.path.abspath(f) for f in args.files], not args.no_ocr,
                          progress=lambda m, f=None: print(f"  {m}"))
        found = job.scan()
        print(f"Found {len(found)} sensitive values.")
        report = job.apply()
        for res in job.results.values():
            state = res.status.upper() + (" (LEAK CHECK WARNING)" if res.leaks else "")
            print(f"  {os.path.basename(res.source)}: {state} {res.replaced} replacements {res.error}")
        print(f"Sanitized copies: {p.sanitized_dir}\nReport: {report}")
    else:
        p = _open(args.project, False, args.password)
        if args.text is not None:
            out, n = restore_text(p, args.text)
            print(out)
            print(f"\n[{n} value(s) restored]", file=sys.stderr)
        else:
            out, n, _ = restore_file(p, args.file)
            print(f"Restored {n} value(s) -> {out}")


if __name__ == "__main__":
    main()
