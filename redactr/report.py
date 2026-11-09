"""HTML + JSON + CSV report of what was found, removed and replaced."""

from __future__ import annotations

import csv
import html
import json
import os
from collections import Counter
from datetime import datetime

from . import APP_NAME, AUTHOR, AUTHOR_URL, __version__
from .categories import CATEGORIES


def write_report(project, profile, sanitizer, results, base_path: str) -> str:
    findings = sanitizer.sorted_findings()
    included = [f for f in findings if f.include]
    excluded = [f for f in findings if not f.include]
    by_cat = Counter()
    for f in included:
        by_cat[f.category] += max(f.replaced, 0)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "app": APP_NAME, "version": __version__, "generated": now, "project": project.name,
        "level": profile.name, "categories": profile.categories, "metadata_stripped": profile.strip_metadata,
        "files": [{"source": r.source, "output": r.output, "status": r.status, "replacements": r.replaced,
                   "leak_check": "passed" if not r.leaks else "WARNING", "possible_leaks": r.leaks,
                   "notes": [n for n in r.notes if not n.startswith("Traceback")], "error": r.error}
                  for r in results],
        "summary": {CATEGORIES[c].label if c in CATEGORIES else c: n for c, n in by_cat.items()},
        "replacements": [{"original": f.original, "category": f.category, "replacement": f.replacement,
                          "occurrences": f.replaced, "files": sorted(f.sources), "detected_by": sorted(f.rules)}
                         for f in included],
        "kept_unchanged_by_user": [{"value": f.original, "category": f.category} for f in excluded],
    }
    with open(base_path + ".json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    with open(base_path + ".csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Original", "Category", "Replacement", "Occurrences", "Files"])
        for f in included:
            w.writerow([f.original, f.category, f.replacement, f.replaced, "; ".join(sorted(f.sources))])

    e = html.escape
    file_rows = "".join(
        f"<tr><td>{e(os.path.basename(r.source))}</td>"
        f"<td>{e(os.path.basename(r.output)) if r.output else '-'}</td>"
        f"<td><span class='pill {'ok' if r.status == 'ok' and not r.leaks else 'bad'}'>"
        f"{'OK' if r.status == 'ok' and not r.leaks else ('LEAK?' if r.leaks else r.status.upper())}</span></td>"
        f"<td class='num'>{r.replaced}</td>"
        f"<td>{e(r.error) if r.error else ''}"
        f"{'<br>'.join(e(n) for n in r.notes if not n.startswith('Traceback'))}"
        f"{('<br><b>Still present:</b> ' + e(', '.join(r.leaks))) if r.leaks else ''}</td></tr>"
        for r in results)
    cat_rows = "".join(f"<tr><td>{e(CATEGORIES[c].label if c in CATEGORIES else c)}</td><td class='num'>{n}</td></tr>"
                       for c, n in by_cat.most_common())
    find_rows = "".join(
        f"<tr><td>{e(f.original)}</td><td>{e(f.category)}</td><td>{e(f.replacement)}</td>"
        f"<td class='num'>{f.replaced}</td><td>{e(', '.join(sorted(f.sources)))}</td></tr>" for f in included)
    excl_rows = "".join(f"<li>{e(f.original)} <small>({e(f.category)})</small></li>" for f in excluded)
    total = sum(r.replaced for r in results)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{APP_NAME} report - {e(project.name)}</title>
<style>
:root{{--midnight:#312C51;--dusk:#48426D;--gold:#F0C38E;--coral:#F1AA9B;--ink:#F7F4FB;--muted:#C9C3E3;--line:#5E5788}}
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:32px;color:var(--ink);background:var(--midnight)}}
h1{{margin:0;font-size:26px}} h1 span{{color:var(--coral)}} h2{{margin-top:32px;font-size:18px;color:var(--gold)}}
a{{color:var(--gold)}} small{{color:var(--muted)}}
.warn{{background:var(--dusk);border-left:4px solid var(--coral);padding:10px 14px;margin:16px 0;border-radius:10px}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}} .card{{background:var(--dusk);border-radius:16px;padding:14px 18px;
min-width:150px;color:var(--muted)}} .card b{{display:block;font-size:24px;color:var(--ink)}}
.card:first-child{{background:var(--gold);color:var(--midnight)}} .card:first-child b{{color:var(--midnight)}}
table{{border-collapse:collapse;width:100%;background:var(--dusk);border-radius:12px;overflow:hidden}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px;vertical-align:top}}
th{{background:var(--gold);color:var(--midnight)}} tr:last-child td{{border-bottom:none}} .num{{text-align:right}}
.pill{{padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600}}
.ok{{background:var(--gold);color:var(--midnight)}} .bad{{background:var(--coral);color:var(--midnight)}}
</style></head><body>
<h1><span>&#1071;</span>edactR sanitization report</h1>
<div>Project <b>{e(project.name)}</b> &middot; {now} &middot; {e(profile.name)}</div>
<div class="warn"><b>Confidential:</b> this report lists the original values. Keep it on this computer -
never upload it to an AI tool. Upload only the files in the <i>sanitized</i> folder.</div>
<div class="cards">
<div class="card"><b>{len(results)}</b>files processed</div>
<div class="card"><b>{total}</b>replacements made</div>
<div class="card"><b>{len(included)}</b>unique values hidden</div>
<div class="card"><b>{'Yes' if profile.strip_metadata else 'No'}</b>metadata wiped</div>
</div>
<h2>Files</h2><table><tr><th>Source</th><th>Sanitized copy</th><th>Status</th><th>Replacements</th><th>Notes</th></tr>{file_rows}</table>
<h2>By category</h2><table><tr><th>Category</th><th>Replacements</th></tr>{cat_rows}</table>
<h2>What was removed and what replaced it</h2>
<table><tr><th>Original (removed)</th><th>Category</th><th>Replaced with</th><th>Times</th><th>Files</th></tr>{find_rows}</table>
{('<h2>Kept unchanged (you un-ticked these)</h2><ul>' + excl_rows + '</ul>') if excluded else ''}
<p><small>Generated locally by {APP_NAME} {__version__} - software by {AUTHOR} (<a href="https://{AUTHOR_URL}">{AUTHOR_URL}</a>). Mapping vault: {e(project.vault_path)}
{'(password protected)' if project.password else '(not password protected)'}.</small></p>
</body></html>"""
    with open(base_path + ".html", "w", encoding="utf-8") as fh:
        fh.write(page)
    return base_path + ".html"
