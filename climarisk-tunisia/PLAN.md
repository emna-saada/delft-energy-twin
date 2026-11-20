# PLAN — ClimaRisk Tunisie

Milestones from brief §9. `[x]` = acceptance criterion met and committed.

- [x] **M0 Research & framing** — `docs/research_log.md` summarises the §4 texts with links and dates; `CLAUDE.md` and `PLAN.md` created.
- [ ] **M1 Repo skeleton** — environment installs cleanly (`uv sync`), CI green, `make test` passes.
- [ ] **M2 Synthetic portfolio** — 2 000 loans in GeoParquet; documented distributions; tests: 24 governorates covered, no coordinate at sea.
- [ ] **M3 Historical hazards** — 4 hazard rasters over Tunisia produced and extracted per asset; PNG maps; tests on tiny data.
- [ ] **M4 Projections** — scores for SSP2-4.5 and SSP5-8.5 at 2030 and 2050 on 5 CMIP6 models; uncertainty (median, p10–p90) displayed.
- [ ] **M5 Credit module** — ΔPD, EL and aggregations; invariant tests; sensitivity analysis.
- [ ] **M6 physrisk comparison** — same assets against OS-Climate physrisk hazard indicators; gaps explained in `docs/methodology.md`.
- [ ] **M7 Dashboard** — runs locally (and on a free host once Emna publishes); 6 tabs of §8.
- [ ] **M8 Report** — 10–15 page PDF: context, regulation, method, illustrative results, limits, compliance matrix.
- [ ] **M9 Video** — 1080p MP4, 2–3 min, follows the §10 storyboard, subtitles, figures from `outputs/kpis.json`.
- [ ] **M10 Final check** — independent sub-agent review: regulatory facts, licences, no personal data, `make demo` reproducibility.

## Needs from Emna
- [ ] Create the public GitHub repo `climarisk-tunisia` (code currently lives in `climarisk-tunisia/` on branch `claude/awesome-galileo-vs1xie` of `delft-energy-twin`).
- [ ] Optional: Earth Engine Community project + `earthengine authenticate` (CHIRPS SPI and MODIS burned-area validation).
- [ ] Re-read BCBS d532 PDF for the exact principle numbering; re-check BCT circulars on bct.gov.tn.
- [ ] Review every assumption in `config/assumptions.yaml`.
