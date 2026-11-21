# Research log

All sources consulted on **2026-11-20** unless stated otherwise. "Verified" means the official page was opened from this environment (HTTP 200) and the statement was read there; "secondary" means confirmed only through press/consultancy summaries; "not verified" means no reliable source could be read.

## 1. Regulatory and normative framework (brief §4)

| # | Text | Status of check | What was confirmed | What the project keeps |
|---|------|-----------------|--------------------|------------------------|
| R1 | BCBS, *Principles for the effective management and supervision of climate-related financial risks* — https://www.bis.org/bcbs/publ/d532.htm | **Verified** (BIS page) + press release p220615 (secondary for the count) | Published **15 June 2022**, status *Current*, 15-page PDF. 18 principles: 1–12 for banks (governance, internal control, capital & liquidity adequacy, risk management, credit/market/liquidity/operational risk, scenario analysis), 13–18 for supervisors. | Compliance matrix maps modules to principles (credit risk, data/reporting, scenario analysis). Exact principle numbering taken from KPMG/BIS summaries; the BIS PDF itself could not be downloaded from this environment (redirect) → **principle-to-number mapping to be re-read in the PDF by Emna**. |
| R2 | BCBS, *A framework for the voluntary disclosure of climate-related financial risks* — https://www.bis.org/bcbs/publ/d597.htm | **Verified** | Published **13 June 2025**, status *Current*, 19 pages. Voluntary; jurisdictions decide whether to implement domestically. Qualitative + quantitative information. | Dashboard "Reporting" tab produces physical-risk exposure tables *inspired by* this framework. |
| R3 | NGFS climate scenarios — https://www.ngfs.net/ngfs-scenarios-portal/data-resources/ | **Verified** | Portal data = **version 5 (Phase V), published 5 November 2024**. Portal notice + NGFS statement of **3 Dec 2025**: **Kotz et al. (2024) has been retracted from *Nature***. Affected: GDP-damage outputs ("Kotz-Wenz" GDP variables, NiGEM physical/combined outputs, REMIND-MAgPIE integrated physical damages). Other Phase V variables are stated as unaffected. NGFS states the next long-term vintage (new physical-risk methodology) is due end-2026; **not published on the portal as of 2026-11-20**. | Use NGFS as narrative; physical hazards driven by CMIP6 SSPs. **We do not use the NGFS/Kotz damage function.** Mapping NGFS ↔ SSP documented in `config/scenarios.yaml`. |
| R4 | EBA, *Guidelines on the management of ESG risks* (EBA/GL/2025/01) — eba.europa.eu press release | **Secondary** (EBA page reachable; dates confirmed via multiple law-firm summaries) | Published **9 January 2025**; apply from **11 January 2026**, small & non-complex institutions at the latest **11 January 2027**. Short/medium/long-term horizons. | European benchmark; horizons today / 2030 / 2050. |
| R5 | ECB, *Guide on climate-related and environmental risks* (Nov 2020) — bankingsupervision.europa.eu | **Verified** (PDF served, HTTP 200) | Final guide, November 2020. | Cited as good practice; report section on Pillar 2 / ICAAP use. |
| R6 | IFRS S2 *Climate-related Disclosures* — ifrs.org | **Verified** | Effective for annual reporting periods beginning on or after **1 January 2024** (issued June 2023). | Outputs follow TCFD/S2 structure (governance, strategy, risk management, metrics). Physical risk only. |
| R7 | BCT circular **91-24** (division, couverture des risques, suivi des engagements) | **Secondary** | Core prudential circular, amended many times; Annex III (collective provisions) replaced by circular **2024-01** (19 Jan 2024). | Referenced as the credit-risk framework; no compliance claim. |
| R8 | BCT circular **2018-06** (normes d'adéquation des fonds propres) | **Secondary** | Dated 5 June 2018; still cited as the capital-adequacy basis by circular 2025-08. Ratio values (10 % / 7 %) **not verified** against the official text → not quoted. | Referenced only. |
| R9 | BCT circulars 2017-06, 2021-01, 2022-01, 2022-02 | **Not verified** | — | Not cited until Emna checks bct.gov.tn. |
| R10 | BCT–KfW technical assistance & **feuille de route 2026-2030** | **Secondary** (Tustex, L'Économiste Maghrébin, La Presse, 4–5 Nov 2026) | Closing ceremony **3 November 2026** chaired by Governor Fethi Zouhaier Nouri; roadmap 2026-2030 with four pillars (incl. climate-risk management & supervision; green-finance instruments & markets; coordination/monitoring). One outlet mentions national mapping of physical risks (drought, flood, sea-level rise). | Positioning: the tool *prepares* banks for future BCT expectations — no claim of regulatory compliance. Exact pillar wording to re-check on bct.gov.tn. |
| R11 | Loi organique n° 2004-63 (données personnelles, INPDP) | **Not verified online** (inpdp.tn unreachable from this environment) | Well-established law reference from the brief. | 100 % synthetic portfolio, stated in README and report. |

## 2. Tools and data

| Item | Check | Result |
|------|-------|--------|
| Earth Engine noncommercial tiers | Verified (developers.google.com guide via search) | Community: 150 EECU-h/month, no billing account; Contributor requires active billing account → **excluded**. Quotas applied from 27 April 2026; annual re-verification. |
| OS-Climate `physrisk-lib` | PyPI + GitHub (secondary) | Apache-2.0; hazard indicators freely available via AWS ASDI. |
| Remotion licence | remotion.dev FAQ | Free for individuals (personal or commercial) and teams ≤ 3 people. |
| NASA NEX-GDDP-CMIP6 | AWS S3 `nex-gddp-cmip6` reachable | Daily tasmax/pr, 0.25°, SSP2-4.5/SSP5-8.5. Blanket **CC0** for all outputs since September 2022 (NASA NEX-GDDP-CMIP6 Tech Note 4; first released under CC BY-SA 4.0). Courtesy attribution kept. |
| WRI Aqueduct Floods | AWS S3 `wri-projects` reachable | CC BY 4.0. |
| ESA WorldCover | AWS S3 reachable | CC BY 4.0. |
| geoBoundaries TUN ADM1 | API reachable | ODbL 1.0 (source OpenStreetMap / Wambacher), as returned by the geoBoundaries API. |

## 2b. Independent review (milestone 10, 2026-11-20)
A sub-agent that did not write the code reviewed facts, licences, personal data and reproducibility. Corrections applied: NEX-GDDP licence → CC0; geoBoundaries → ODbL; Piper TTS (GPL-3.0, CLI only) and voice datasets added to the licence register; Kotz retraction scope narrowed to the GDP-damage outputs; BCBS d532 status downgraded to "page verified, numbering to re-read"; synthetic disclaimer shown on the video results screen; additional EL also reported *vs today*; report uncertainty sentence now computed from outputs.

## 3. Decisions taken
- Physical hazards from **CMIP6 (NEX-GDDP)** for heat & drought, **Aqueduct** for floods, **WorldCover + climate** for wildfire; ERA5-Land (needs a CDS account) replaced by the NEX-GDDP historical run for the baseline (documented limitation).
- No NGFS damage function (retracted Kotz et al. 2024) — PD uplift uses an explicit, illustrative elasticity β with sensitivity analysis.
