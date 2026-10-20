#!/usr/bin/env python3
"""Copy the dashboard, assets and recorded results into docs/ for GitHub Pages.

    python scripts/build_site.py

docs/index.html (the story page) is hand-written and reads docs/results/index.json,
so after new runs this script is all you need to refresh the site. No API key is
involved: the published site only reads recorded results.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def main() -> None:
    # Dashboard: same file as the local one, with a static-site navigation bar.
    html = (ROOT / "app" / "dashboard.html").read_text()
    html = html.replace(
        '<a href="index.html" id="nav-type">Type</a>',
        '<a href="index.html" id="nav-type">Story</a>',
    )
    (DOCS / "dashboard.html").write_text(html)

    # Shared assets (stylesheet and vendored fonts).
    shutil.copytree(ROOT / "app" / "assets", DOCS / "assets", dirs_exist_ok=True)

    # Recorded runs: every results/<version>/<run>.json plus the index.
    out = DOCS / "results"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy2(ROOT / "results" / "index.json", out / "index.json")
    n = 0
    for path in sorted((ROOT / "results").glob("v*/*.json")):
        (out / path.parent.name).mkdir(exist_ok=True)
        shutil.copy2(path, out / path.parent.name / path.name)
        n += 1
    (DOCS / ".nojekyll").write_text("")
    print(f"docs/ refreshed: dashboard, assets, {n} runs")


if __name__ == "__main__":
    main()
