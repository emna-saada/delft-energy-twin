# CLAUDE.md — ClimaRisk Tunisie

Rules for any Claude Code session working on this repository (from brief §3). Re-read every session.

1. **Free only.** No paid service, no credit card, no trial requiring a payment method. Earth Engine: *Community* noncommercial tier only (150 EECU-h/month) — never *Contributor* (requires a billing account). Prefer openly downloadable data (AWS Open Data, Copernicus, JRC) and local compute.
2. **Verified licences.** Check and record the licence of every library and dataset in `docs/LICENSES_DATA.md`. Project code is MIT. CLIMADA is GPL-3.0: optional, isolated dependency only, never copy its code.
3. **No personal data.** The portfolio is 100 % synthetic (Tunisian organic law n° 2004-63, INPDP). No real client name, no real bank data. README says so.
4. **Research first, code second.** Read official documentation before each milestone; log it in `docs/research_log.md` (source, date, what was kept). Never invent a regulatory reference, circular number or figure. Write « non vérifié » / "not verified" when a source could not be checked.
5. **Plan then execute.** Keep `PLAN.md` ticked; commit small and often with clear messages.
6. **Tests & reproducibility.** `pytest` per module with tiny test data in-repo; fixed random seed; locked `pyproject.toml`; `make demo` reproduces end-to-end; GitHub Actions CI.
7. **Explicit assumptions.** Every coefficient (sector vulnerability, PD elasticity β, thresholds) lives in `config/assumptions.yaml` with a source or the mention "illustrative assumption". Sensitivity analysis is mandatory.
8. **Honest results.** Portfolio figures are *illustrative* — never present them as real losses of a Tunisian bank. State limits: resolution, climate-model bias, retraction of Kotz et al. (2024) used by NGFS Phase V damage functions.
9. **Vocabulary.** Write « géoinformatique », never « géomatique ». Code & technical docs in English; report and video in French (English optional).
10. **Ask before acting** on anything irreversible or public: publishing the repo, LinkedIn posts, e-mails. Emna validates.

Figures in the video and the report come **only** from `outputs/kpis.json` produced by the pipeline.
