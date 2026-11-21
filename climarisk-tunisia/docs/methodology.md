# Methodology — ClimaRisk Tunisie

Technical companion of the French PDF report (`docs/report.pdf`). All numbers below are produced by
`make run` and stored in `outputs/kpis.json`; they describe a **100 % synthetic portfolio** and are illustrative.

## 1. Pipeline

```
config/*.yaml ─┐
data/raw/ ─────┼─> portfolio.py ─> hazards/ (climate, flood, wildfire, scoring) ─> vulnerability.py ─> credit.py
               │                                                                          │
               └──────────────────────────────────────────────────────────────> pipeline.py ─> outputs/
                                                                                     ├─ kpis.json (single source for report + video)
                                                                                     ├─ asset_results.parquet, by_*.csv, sensitivity.csv
                                                                                     └─ maps/*.png
```

| Step | Module | Notes |
|---|---|---|
| Synthetic portfolio | `portfolio.py` | 2 000 loans, seed 2026, locations from WorldPop / WorldCover cropland / 3 km coastal buffer, redrawn until inside their governorate polygon. EAD rescaled to target sector shares of a 3 bn TND book. |
| Climate indicators | `scripts/fetch_cmip6.py`, `hazards/climate.py` | NEX-GDDP-CMIP6 daily tasmax/pr, 5 models. Annual hot35, hot40, CDD, total precipitation; 3-year means per horizon; precipitation change relative to the same model's 2010-2014 run. |
| Flood | `scripts/fetch_flood.py`, `hazards/flood.py` | WRI Aqueduct v2 RP100, max(riverine, coastal). Future riverine: 5 GCMs; coastal: 50th percentile sea-level. |
| Wildfire | `hazards/wildfire.py` | Burnable-vegetation share in a 2 km window (WorldCover classes weighted) × fire weather (mean of heat and drought scores). |
| Scores | `hazards/scoring.py` | Linear, clipped, fixed physical bounds (see `config/assumptions.yaml`), so scores are monotone and comparable across scenarios. |
| Composite | `vulnerability.py` | Vulnerability-weighted mean of hazard scores per sector. |
| Credit | `credit.py` | PD_s = min(1, PD·(1+β·Score)); LGD uplift γ·flood for land / real-estate collateral; EL = PD·LGD·EAD. High-hazard zone = a hazard material for the sector (V ≥ 0.5) with score ≥ 0.6. |
| Uncertainty | `credit.ensemble_summary` | CMIP6 model *k* paired with Aqueduct GCM *k* (arbitrary pairing → pseudo-ensemble); median and 10–90 % across the 5 realisations. Flood baseline is WATCH-forced while futures are GCM-forced, so today-vs-future flood changes are not like-for-like. |

## 2. NGFS ↔ SSP mapping

NGFS Phase V (Nov 2024) is used as narrative only. SSP2-4.5 proxies the physical side of *NDCs / Delayed Transition*; SSP5-8.5 is used as an upper physical stress bound (above *Current Policies*). The NGFS GDP-damage function (Kotz et al., 2024; "Kotz-Wenz" variables) is **not** used — the paper was retracted from *Nature* (NGFS statement, 3 Dec 2025); NGFS states other Phase V variables are unaffected.

## 3. Illustrative results (synthetic portfolio)

| Period | EAD in high-hazard zone | Additional EL | bp of EAD |
|---|---|---|---|
| Today (2010-2014 climate) | 1.5 % | 4.6 M TND | 15.5 |
| SSP2-4.5 · 2030 | 3.0 % | 5.2 M TND | 17.4 |
| SSP2-4.5 · 2050 | 16.9 % | 7.9 M TND | 26.5 |
| SSP5-8.5 · 2030 | 8.7 % | 6.5 M TND | 21.6 |
| SSP5-8.5 · 2050 | 22.4 % (band 18.7–44.3 %) | 8.8 M TND (band 8.0–10.4) | 29.5 |

Most affected sectors (SSP5-8.5 2050, bp of sector EAD): cereals (84), olives (71), construction (48), citrus (43) — driven by drought and heat. "Today" is non-zero because base PDs are treated as climate-neutral (assumption); the increment versus today is reported separately in `kpis.json` (`el_add_vs_today_tnd`, median of per-model differences: +4.8 M TND for SSP5-8.5 2050).

## 4. Milestone 6 — comparison with OS-Climate physrisk

We sampled physrisk's published hazard indicators (s3://os-climate-physical-risk) at the same 2 000 locations (`src/climarisk/physrisk_compare.py`, output `outputs/physrisk_comparison.*`). We used the hazard indicator layer rather than running the full physrisk vulnerability engine, whose sector damage curves do not match our credit framing.

| Indicator | Ours | physrisk | Agreement |
|---|---|---|---|
| Heat (ACCESS-CM2) | days Tmax > 35 °C: 36 → 68 d/yr | days T**mean** > 35 °C: 0.2 → 2.5 d/yr | Spearman 0.66 (today), 0.88 (2050) |
| Drought | score from CDD + precipitation change | months/yr SPEI-12 < −1.5, multi-model: 0.6 → 4.5 | both: worsening for 100 % of assets; spatial rank Spearman −0.65 (2050) |

**Why the gaps.** (1) Heat: physrisk's indicator uses daily mean temperature, far rarer above 35 °C than daily maximum, so levels differ by an order of magnitude while the spatial ranking agrees well. (2) Drought: SPEI is *standardised* against each cell's own climate, so it highlights the relative drying of the wetter north; our CDD-based score is absolute and peaks in the arid south. Neither is "right": for rain-fed agriculture in the north the standardised view is arguably more relevant, which argues for a sector-specific drought indicator in a next version.

## 5. Validation

- Unit tests (`pytest`): scores in [0,1] and monotone in intensity; PD/LGD in [0,1]; zero hazard ⇒ zero additional EL; aggregations conserve EAD and EL; ensemble band ordered; β sensitivity monotone; portfolio inside polygons, reproducible with the seed; M2 acceptance (2 000 loans, 24 governorates, none at sea).
- Spatial plausibility: high flood depths in the Medjerda valley, Cap Bon and Nabeul coastal plains (cf. Nabeul floods of September 2018); fuel concentrated in the Kroumirie / Mogods forests of the north-west.
- Not yet done: quantitative validation against MODIS MCD64A1 burned area and CHIRPS-based SPI via Earth Engine (needs Emna's Community-tier authentication); ERA5-Land / station comparison for heat.

## 6. Limits

See report §9: synthetic portfolio, 0.25° climate resolution, 5 models × 3-year windows (2030 dominated by interannual variability), CMIP5-based Aqueduct, uncalibrated β/γ/vulnerability, physical risk only.
