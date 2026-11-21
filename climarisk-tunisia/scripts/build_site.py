"""Assemble the static results site in site/ (deployable as-is to GitHub Pages).

Steps: export the dashboard tables from outputs/ (scripts/export_dashboard_data.py), copy them into
site/data, and copy the maps, the PDF report and the demo video into site/downloads.
Run after `make run maps report`. Preview locally with `python -m http.server -d site`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts/export_dashboard_data.py")], check=True)
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "outputs/dashboard").glob("*.json"):
        shutil.copy2(f, SITE / "data" / f.name)
    dl = SITE / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    from climarisk.paperfigs import render_all  # English journal-style figures for the site

    render_all(("en",))
    for src, dst in (("fig_heat", "map_heat"), ("fig_drought", "map_drought"), ("fig_flood", "map_flood"),
                     ("fig_fire", "map_fire"), ("fig_portfolio", "map_portfolio"), ("fig_gov", "map_el_governorate")):
        shutil.copy2(ROOT / f"outputs/paper/en/{src}.png", dl / f"{dst}.png")
    shutil.copy2(ROOT / "docs/report.pdf", dl / "report.pdf")
    video = ROOT / "video/out/climarisk_demo.mp4"
    if video.exists():
        shutil.copy2(video, dl / "climarisk_demo.mp4")
    (SITE / ".nojekyll").write_text("")
    print("site ready:", SITE)


if __name__ == "__main__":
    main()
