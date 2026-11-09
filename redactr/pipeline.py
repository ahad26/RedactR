"""High level jobs used by both the desktop app and the command line."""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass, field

from . import formats
from .engine import Replacer, Restorer, Sanitizer
from .levels import Profile
from .project import Project, timestamp
from .report import write_report


@dataclass
class FileResult:
    source: str
    output: str = ""
    status: str = "pending"      # ok / error / skipped
    replaced: int = 0
    leaks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    error: str = ""


class SanitizeJob:
    """scan() -> (user reviews findings) -> apply()"""

    def __init__(self, project: Project, profile: Profile, files: list[str], use_ocr: bool = True,
                 progress=None):
        self.project = project
        self.profile = profile
        self.files = files
        self.use_ocr = use_ocr
        self.progress = progress or (lambda msg, frac=None: None)
        self.sanitizer = Sanitizer(profile, project.vault)
        self.extracted: dict[str, formats.Extracted] = {}
        self.results: dict[str, FileResult] = {f: FileResult(f) for f in files}

    # ---------------------------------------------------------------- scan
    def scan(self):
        n = len(self.files)
        forced_all = []
        for i, f in enumerate(self.files):
            self.progress(f"Reading {os.path.basename(f)}", i / max(n, 1))
            try:
                ex = formats.extract(f, self.use_ocr)
            except Exception as exc:
                r = self.results[f]
                r.status, r.error = "error", str(exc)
                continue
            self.extracted[f] = ex
            self.results[f].notes += ex.notes
            name = os.path.basename(f)
            for loc, text in ex.texts:
                self.sanitizer.scan(text, name)
            forced_all += [(v, c, name) for v, c, _loc in ex.forced]
        for v, c, src in forced_all:
            self.sanitizer.add_forced(v, c, src)
        self.sanitizer.derive_org_names([(os.path.basename(f), t) for f, ex in self.extracted.items()
                                         for _loc, t in ex.texts])
        self.progress("Scan complete", 1.0)
        return self.sanitizer.sorted_findings()

    # ---------------------------------------------------------------- apply
    def apply(self, out_dir: str | None = None) -> str:
        out_dir = out_dir or self.project.sanitized_dir
        os.makedirs(out_dir, exist_ok=True)
        replacer = self.sanitizer.plan()
        numeric = any(c in self.profile.categories for c in ("NUMBER", "MONEY"))
        n = len(self.extracted)
        for i, (f, ex) in enumerate(self.extracted.items()):
            r = self.results[f]
            self.progress(f"Sanitizing {os.path.basename(f)}", i / max(n, 1))
            before = sum(replacer.counts.values())
            try:
                out = os.path.join(out_dir, formats.output_name(f, ex.work_path, "sanitized"))
                r.notes += formats.write_copy(f, ex.work_path, out, replacer, strip_metadata=self.profile.strip_metadata,
                                              numeric=numeric, use_ocr=self.use_ocr)
                r.output = out
                r.replaced = sum(replacer.counts.values()) - before
                r.status = "ok"
                r.leaks = self._leak_check(out)
            except Exception as exc:
                r.status, r.error = "error", f"{exc}"
                r.notes.append(traceback.format_exc(limit=2))
        self.sanitizer.collect_counts(replacer)
        self.project.save()
        self.progress("Writing report", 0.98)
        report = write_report(self.project, self.profile, self.sanitizer, list(self.results.values()),
                              os.path.join(self.project.reports_dir, f"report_{timestamp()}"))
        self.progress("Done", 1.0)
        return report

    def _leak_check(self, out_path: str) -> list[str]:
        """Re-read the written file and look for any original value that survived."""
        if formats.ext_of(out_path) in formats.IMG_EXT:
            txt = os.path.splitext(out_path)[0] + ".txt"
            text = open(txt, encoding="utf-8").read() if os.path.isfile(txt) else ""
        else:
            text = formats.read_back_text(out_path)
        keys = {f.key for f in self.sanitizer.findings.values() if f.include}
        checker = Replacer([(o, "x", cs) for o, _r, cs in self.project.vault.forward_pairs(keys)])
        return sorted({text[s:e] for s, e, _r, _k in checker.matches(text)})


# =================================================================== restore
def restore_text(project: Project, text: str) -> tuple[str, int]:
    out, counts = Restorer(project.vault).restore_text(text)
    return out, sum(counts.values())


def restore_file(project: Project, path: str, out_dir: str | None = None) -> tuple[str, int, list[str]]:
    out_dir = out_dir or project.restored_dir
    ex = formats.extract(path, use_ocr=False) if formats.ext_of(path) in formats.LEGACY_EXT else None
    work = ex.work_path if ex else path
    stem = os.path.splitext(os.path.basename(path))[0]
    for suffix in ("_sanitized",):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    out = os.path.join(out_dir, f"{stem}_restored{formats.ext_of(work)}")
    rep = Restorer(project.vault).new_replacer()
    notes = formats.write_copy(path, work, out, rep, strip_metadata=False, numeric=True, use_ocr=False, restore=True)
    return out, sum(rep.counts.values()), notes
