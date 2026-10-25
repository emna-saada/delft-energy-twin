# PLAN — LiDAR Energy Digital Twin of Delft

## Decisions taken at setup (25 Oct 2026)

- **Main epoch is AHN6, not AHN5.** AHN6 over Delft was flown on **19 Dec 2025 (south) and 19 Jan 2026 (north)** and
  published on 9 Oct 2026, in 1×1 km LAZ tiles (165–313 MB) at 20–31 building pts/m². AHN5 (2023) and AHN4 cover Delft
  only as 5×6.25 km tiles of 5–8.5 GB each, so they are used as DSM rasters for change detection instead of point clouds.
- **Data source:** official AHN downloads (`basisdata.nl`, `fsn1.your-objectstorage.com/hwh-ahn`), found through the
  AHN dataroom's WFS tile index. GeoTiles and `data.3dbag.nl` (TU Delft servers) time out from this network.
- **AOIs come from official CBS 2024 boundaries:** Binnenstad (WK050311, 1.48 km²), TU campus (BU05032801 + BU05032805,
  1.07 km²), Voorhof (WK050324, 1.27 km²). Total 3.81 km² in 14 AHN6 tiles; 100 m shadow buffer.
- PDAL is replaced by `laspy` + numpy, and Open3D by our own numba region growing (no heavy Windows dependencies).
- Leaf-off flights (Dec/Jan): tree crowns are under-sampled → tree shading is a stated limitation and needs a sensitivity run.

## Stages

| # | Stage | Status | Output |
|---|-------|--------|--------|
| 1 | Data: AOIs, AHN6 tile index, LAZ/DSM/DTM, BAG panden, 2025 3D reference | done, 14 tiles | `configs/aois.geojson`, `data/raw/` |
| 2 | Preprocess: SOR outliers, DTM/DSM/nDSM/vegetation 0.5 m | done, 14 tiles | `data/processed/<tile>/*.tif` |
| 3 | Roof planes per footprint (region growing), walls > 70° dropped, obstacles; tile-edge buildings handled | done, 14 tiles | `<tile>/roof_planes.parquet` |
| 4 | Solar: horizon scan (72 dirs, 200 m) + sun map, Hay-Davies sky, trees with seasonal τ, PVGIS TMY; city DSM mosaic | done, 14 tiles | `city/roof_irradiation_kwh_m2.tif`, `city/roof_planes_solar.parquet` |
| 4b | Tree sensitivity: crown transmissivity and crown extent (study-area buildings) | done | `city/tree_sensitivity.csv` |
| 4c | AHN5 → AHN6 change: new / raised / lowered buildings, demolitions, installed PV epoch | done | `city/change_*.parquet`, `city/change_stats.json` |
| 5 | PV layout, hourly self-consumption, battery, 2026 vs 2027 value | done (technical potential) | `city/pv_planes.parquet`, `city/pv_buildings.parquet`, `city/pv_summary.json` |
| 6a | Indicative heritage filter: technical vs permitted potential | done | `city/heritage_summary.json`, `city/heritage_buildings.parquet` |
| 6b | Per-buurt aggregation, building attributes, CityJSON 2.0 + 3D Tiles 1.1 export | done | `web/public/data/` |
| 7 | Validation: LoD2 reference, PVGIS, campus vs Zhou et al., Monte Carlo uncertainty | done | `results/metrics.json` |
| 8 | Website (Vite + CesiumJS + MapLibre + ECharts), GitHub Pages workflow | first version done, verified locally | `web/`, `.github/workflows/pages.yml` |

Run everything: `python -m delft_twin.pipeline preprocess --all --workers 3`, then `segment --all`, `validate --all`,
`solar --all`, `city`; then `python -m delft_twin.sensitivity`, `python -m delft_twin.change`, `python -m delft_twin.pv`
(also writes the campus comparison), `python -m delft_twin.heritage`, `python -m delft_twin.uncertainty`,
`python -m delft_twin.export`, `python -m delft_twin.mesh`, `python -m delft_twin.figures`. On Windows redirect output to a file (`cmd /c "... > log.txt 2>&1"`): piping through
PowerShell `2>&1 | Out-File` stalled the process. Kernel speed varied 7× between runs on this laptop (CPU availability);
outputs were verified identical.

## Tile-edge handling (city.py)

- Each BAG building is **owned by one tile** — the tile holding its representative point — so nothing is processed twice.
- A tile's segmentation **gathers building points from every processed tile** overlapping its owned footprints, so
  buildings crossing a border are reconstructed from their complete point set (**412 such buildings**).
- Shading uses **one city DSM mosaic** (ours inside the 14 tiles, official AHN6 DSM in the 100 m ring) so shadows cross borders.
- 184 buildings reach outside the 14 tiles and are skipped — **none of them in a study area**.

## Results, all 14 tiles (31,216 buildings processed; 30,598 validated)

| Area | Buildings | Sky-visible roof area | Flat share | Median kWh/m²/yr | Loss to obstructions | of which trees |
|---|---|---|---|---|---|---|
| Binnenstad | 4,220 | 0.485 km² | 34 % | 820 | 24.7 % | 0.8 % |
| TU campus | 276 | 0.220 km² | 56 % | 943 | 20.3 % | 0.9 % |
| Voorhof | 1,420 | 0.215 km² | 79 % | 961 | 20.6 % | 1.6 % |
| Rest of the 14 tiles | 24,709 | 1.744 km² | 51 % | 995 | 14.4 % | 1.5 % |

"Sky-visible" = cells where the plane is the top surface; summed plane area is 11 % larger (overhangs, stacked
levels). **PV potential must use sky-visible area** (`area_top_3d_m2`).

## Validation vs Kadaster 3D Basisvoorziening 2025

Reference: Kadaster 3D Basisvoorziening 2025 (PDOK), built with `roofer` — the 3DBAG tool — on AHN5 2023.
It replaces 3DBAG, whose servers are unreachable from this network. Different LiDAR epoch → independent check.

| Check (all tiles) | Result |
|---|---|
| Planes ≥ 10 m² matched to a reference LoD2.2 roof surface | 99.3 % |
| Slope error | median 0.60° (Binnenstad 0.78°, campus 1.57°, Voorhof 0.80°) |
| Aspect, pitched roofs within 15° | 99.0 % Binnenstad, 90.8 % campus, 98.8 % Voorhof |
| Vertical offset plane → reference surface | median 0.053 m; 93 % < 0.5 m (Binnenstad 96 %, campus 90 %, Voorhof 77 %) |
| Roof height (70th pct) vs reference, in NAP | median abs. error **0.052 m** over 30,598 buildings (bias +0.02 m, RMSE 0.27 m on single-part buildings) |
| Irradiance vs PVGIS 5.3, unshaded planes (4,069 planes, 40 bins) | raw bias −3.6 %, RMSE 4.0 %; TMY-adjusted bias −1.2 %, RMSE 1.8 % |

**Correction to the earlier test-tile note:** the +0.5 m height bias was *not* a definition difference. The reference's
`rf_h_roof_*` attributes are heights **above ground** (`rf_h_ground`, NAP). Evidence: (ours − ref) correlates 0.95 with
`rf_h_ground`; the southern polder tiles (ground ≈ −1.6 m NAP) showed −1.6 m, the centre (≈ +0.3 m NAP) +0.3–0.5 m.
After adding ground, every tile is within ±3 cm.

Where planes sit ≥ 0.5 m from the reference surface (7 %), two causes dominate:
1. **Real change after 2023** — buildings completed in 2023–2026 are 4–14 m higher in AHN6 than in AHN5; the reference
   predates them. This is the AHN5 → AHN6 change signal for the side analysis.
2. **Multi-level roofs** on 1960s high-rise blocks (Voorhof): planes ~4 m below the main roof (podiums, setbacks,
   terraces, some access galleries) that the reference LoD2.2 generalises away; 77 % of their area is sky-visible.
Plus a small **existing-PV signature**: 2–3 % of planes are tilted ~15° (E/S/W mix) 0.15–1.5 m above flat reference
roofs (≈ 31,800 m² total) — input for an "already installed PV" layer.

Fixes made because of validation:
- Planes steeper than 70° were façade/parapet points (1,254 of them sat on flat reference roofs) → dropped as walls.
- Isotropic sky under-predicted sun-facing roofs by 7–10 % vs PVGIS → switched to Hay–Davies (circumsolar shaded with the beam).
- BAG filter dropped 'Verbouwing pand' (under renovation), which removed two medieval buildings (1381, 1414) → now kept.
- Reference heights converted from above-ground to NAP.

## Tree-shading sensitivity (study-area buildings)

AHN6 is leaf-off, so crowns are under-sampled. Six scenarios: τ (leaf-on / leaf-off) sparse 0.5/0.9, base 0.3/0.7,
dense 0.1/0.5, opaque 0/0; and base τ with every crown grown by 1 m or 2 m (grey dilation of the tree surface).

| Tree loss of roof irradiation | sparse | base | dense | opaque | crown +1 m | crown +2 m |
|---|---|---|---|---|---|---|
| Binnenstad | 0.5 % | 0.8 % | 1.1 % | 1.5 % | 1.2 % | 2.0 % |
| TU campus | 0.6 % | 0.9 % | 1.3 % | 1.7 % | 1.3 % | 1.7 % |
| Voorhof | 1.0 % | 1.6 % | 2.2 % | 2.9 % | 2.2 % | 3.0 % |
| Buildings losing > 10 % (Binnenstad / campus / Voorhof) | 2 / 12 / 8 % | 4 / 19 / 13 % | 6 / 24 / 19 % | 9 / 32 / 24 % | 8 / 27 / 21 % | 14 / 37 / 30 % |

**Finding:** trees hardly change district potential (≤ 3 % in every scenario) but strongly change which *individual*
buildings are affected (2–4× between scenarios). Building-level advice must show this range.

## AHN5 (2023) → AHN6 (2025/26) change

- Noise on unchanged buildings: median −0.2 cm, NMAD 3.1 cm → the 1 m change threshold is very conservative.
- 85 new buildings, 412 raised / extended, 81 lowered, 30,597 unchanged (31,175 complete buildings).
- Validation vs BAG: 96.5 % of detected new buildings have bouwjaar ≥ 2023; recall 94 % (49 / 52) for buildings with
  bouwjaar ≥ 2024, ≥ 30 m², on a site empty in 2023. Raw recall over all bouwjaar ≥ 2024 is 58 %: of the 44 misses,
  30 are < 30 m² (sheds) and 25 had a structure on site in 2023 (rebuilds, shells standing during the AHN5 flight).
- Demolitions: 219 footprints of the 2023 BAG (Kadaster hoogtestatistieken 2023) are not in the current BAG;
  60 confirmed demolished by AHN6 (9,240 m²), 72 replaced by a new building on the same site.
- Installed PV on flat roofs (PV-like planes): 620 arrays / 22,900 m² already present in 2023;
  **354 arrays / 6,400 m² installed between 2023 and 2026**; 84 unclear.
- Caveat: both DSMs include tree canopy, so "raised" / "lowered" can include crown growth or pruning over roofs.

## PV potential and value (technical potential, before heritage rules)

Layout: modules 430 Wp / 1.95 m², PR 0.80; pitched roofs flush (packing 0.85), flat roofs east-west 12° (GCR 0.70,
captures 98.8 % of horizontal irradiation); 0.5 m setback from ridges, steps and obstacles (the roof outline is
already 0.5 m inside the footprint); suitable = contiguous panel field ≥ 10 m² with ≥ 650 kWh/m²/yr on the module.
Demand: dwellings (BAG, buildings with woonfunctie) × CBS 2024 grid delivery per dwelling (buurt), shaped by the
MFFBAS/NEDU 2026 E1A profile for connections without PV. Prices: CBS 85592NED, Oct 2025 – Sep 2026 average:
retail €0.260/kWh (supply + energy tax, incl. VAT); 2027 export €0.060/kWh = 50 % of the bare supply tariff (excl. VAT).

| | Binnenstad | TU campus | Voorhof |
|---|---|---|---|
| Buildings with potential | 2,456 / 4,259 | 191 / 284 | 886 / 1,434 |
| kWp | 24,700 | 15,400 | 20,000 |
| GWh/yr (all buildings) | 18.7 | 11.5 | 15.1 |
| Residential demand covered | 70 % | 44 % | 57 % |
| Self-consumption (no battery → 5 kWh/dwelling) | 37 → 57 % | 55 → 76 % | 46 → 64 % |
| Change in value at the end of net metering | **−34 %** (−15 % with battery) | −27 % (−10 %) | −28 % (−11 %) |

(Values updated after the NaN fix in the hourly balance: 34 small planes had blanked some buurt hourly sums.)

Specific yield of PV planes: median 786 kWh/kWp (p10 580, p90 898); 49 % within ±10 % of the 875 kWh/kWp norm —
good roofs sit at the norm, the median includes east/west, partly shaded and flat-roof planes, and the TMY is 2.5 %
darker than the 2005–2023 mean. Midday export peaks (residential only) reach 1.4–1.7 MW per buurt (Centrum,
Centrum-Oost, Multatulibuurt), at 13–14 h local time on clear June days.

Fixes made because of PV checks:
- Usable area was 31–54 % of sky-visible roof: speckle between over-segmented coplanar fragments and unlabelled holes
  were treated as edges. Now holes are filled by neighbour majority and the setback applies only at incompatible
  planes (> 10° or > 0.3 m apart) and obstacles.
- The outline got a double setback (footprint inner buffer 0.5 m + PV setback 0.5 m) → PV setback no longer applies at
  the outline. Binnenstad test tile: usable share 36 % → 53 %.
- Battery value counted round-trip losses as self-consumption → now uses demand covered by PV.

## Heritage filter: technical vs permitted potential (indicative)

Rules encoded from Delft's protected-cityscape solar policy as reported by Solar Magazine (2019): since 1 May 2012
panels are allowed in the protected cityscape only out of view from public space; the quick check allows side roof
faces ≥ 4 m behind the front facade and excludes roof faces bordering public space (e.g. the Nieuwe Kerk). The current
municipal criteria could not be confirmed online — **this layer is indicative and must be checked with the gemeente**.

- Protected areas: RCE beschermde stads- en dorpsgezichten (PDOK) — "Delft" (centre), "Delft – TU-Noord", "Nieuwe
  Plantage". 4,156 of 4,259 Binnenstad buildings and 116 of 284 campus buildings lie inside; Voorhof none.
- Public space: BGT wegdeel (roads, footpaths, squares, parking) + waterdeel (canals), current objects at ground level.
- Front facade: a ≤ 1 m piece of the footprint outline whose outward line of sight reaches public space within 15 m
  before another building. A first version (outline within 1.5 m of public space) found fronts for only 37 % of protected
  Binnenstad buildings, because BGT maps private front strips ("stoep", erf) and verges between facade and street;
  line of sight finds 58 % (the rest are rear annexes and back houses registered as separate BAG panden) and 90 % on campus.
- Not permitted: usable cells < 4 m from a front facade, and pitched cells sloping down towards a front facade.
- Rijksmonumenten (RCE points in the footprint, or > 50 % covered by an RCE monument polygon): "permit required"
  (562 buildings in the Binnenstad, 14 on campus). Municipal monuments are not in this layer.
- Each scenario re-checks panel-field suitability (≥ 10 m², ≥ 650 kWh/m²) on the remaining cells.
- Check: of 20,000 sampled "permitted" cells none lies < 3.5 m from a detected front (0.2 % at 3.8–4.0 m: raster rounding).

| | Technical | Permitted incl. monuments with permit | Permitted without permit |
|---|---|---|---|
| Binnenstad GWh/yr | 18.7 | 14.5 (78 %) | 10.7 (57 %) |
| Binnenstad kWp | 24,700 | 19,200 | 14,100 |
| Binnenstad buildings with PV | 2,456 | 1,956 | 1,605 |
| Binnenstad residential demand covered | 70 % | 52 % | 38 % |
| Binnenstad value 2027 rules (M€/yr, homes) | 1.68 | 1.31 | 1.02 |
| Campus GWh/yr | 11.5 | 10.3 (90 %) | 9.6 (84 %) |

**Finding:** in the historic centre the visibility rules remove about a fifth of the technical potential, and if
monuments cannot get a permit another fifth is lost; permit policy for rijksmonumenten matters as much as the
visibility rule itself.

## Campus comparison with Zhou et al.

Reference: Zhou, Verkou, Zeman, Ziar & Isabella, *Solar RRL* 6(5) 2100478 (2022), read from the full text
(`data/raw/literature/zhou_2022_solar_rrl.pdf`, CC BY-NC-ND). Verified (p. 15): ≈ 8.1 GWh/yr in total, of which
**roofs ≈ 4.7 GWh/yr** and facades ≈ 3.4 GWh/yr; campus demand 82.6 GWh/yr. Scope: "all the buildings of TU Delft
campus" — no building list or boundary is given.

Their method vs ours:

| | Zhou et al. | This study |
|---|---|---|
| LiDAR | AHN3, campus flown 2014, 3–5 pts/m² stated (6–10 in another section); trees opaque | AHN6 (Dec 2025 / Jan 2026), ~25 pts/m²; trees with seasonal τ |
| Irradiance | simplified skyline model, coefficients for Delft climate (dataset not named) | horizon scan + Hay–Davies on PVGIS TMY (SARAH-3, 2005–2023) |
| Module | Solarge 365 Wp, 2.066 × 0.997 m (177 Wp/m²) | 430 Wp, 1.95 m² (221 Wp/m²) |
| Flat roofs | module fitting; dual-tilt 12° with 0.2 m clearance (best for most roofs) or 15° rows, 0.7 m spacing | east-west 12°, GCR 0.70 |
| Selection | drop a module if any of its points gets < 600 kWh/m²/yr, or its yield < 650 kWh/kWp | drop a panel field < 10 m² or with mean < 650 kWh/m² on the module (≈ 520 kWh/kWp) |
| Losses | SNL inverter model + MPPT 0.98, ohmic 0.99, mismatch 0.99, soiling 0.98 | PR 0.80 |
| Heritage | flat-mounted (0°) modules on monuments / protected-view buildings | technical potential (heritage filter separate) |

Moving our campus estimate (non-residential buildings in CBS TU-Noord + TU-Campus) step by step to their assumptions:

| Step | Buildings | kWp | Roof GWh/yr | vs Zhou roofs 4.7 |
|---|---|---|---|---|
| Ours (technical, 2026 campus) | 178 | 13,000 | 9.65 | 2.05× |
| + Zhou module density (177 vs 221 Wp/m²) | 178 | 10,450 | 7.76 | 1.65× |
| + Zhou economic threshold (≥ 650 kWh/kWp) | 178 | 8,470 | 6.56 | 1.40× |
| + only buildings with bouwjaar ≤ 2014 (their AHN3 campus) | 127 | 8,020 | 6.21 | 1.32× |

**Finding:** module density, the economic threshold and the 2014 vs 2026 building stock explain most of the 2×
difference (9.65 → 6.2 GWh/yr). The remaining ~30 % has identified but unquantified candidates: their per-module
"any point < 600 kWh/m²" rule (stricter than our field mean), opaque trees, flat-mounted modules on the 116 campus
buildings inside the TU-Noord protected view and on monuments, and scope (TU-owned buildings vs all non-residential
buildings in two CBS buurten). With all differences accounted for as far as the paper allows, the two estimates agree to
within about a third — consistent for two independent LiDAR epochs 12 years apart.

## Monte Carlo uncertainty (Biljecki-style)

Five independent factors, 2,000 draws per study area:
- geometry — per-building height offset σ = 0.27 m (validation RMSE) and per-plane normal noise σ ≈ 1.5°; the shading
  kernel was re-run 30 times on a fixed 10 % sample of study-area roof cells (320,700 cells), paired with a base run;
- weather — each PVGIS-SARAH3 year 2005–2023 instead of the TMY, transposed per panel orientation;
- performance ratio U(0.75, 0.85); tree transmissivity between the 'sparse' and 'dense' scenarios;
  flat-roof ground coverage U(0.55, 0.75) applied to the flat-roof share of yield.

| GWh/yr, median (5–95 %) | Technical | Permitted incl. permit | Permitted without permit |
|---|---|---|---|
| Binnenstad | **18.5 (16.6–20.7)** | 14.4 (12.9–16.1) | 10.6 (9.5–11.9) |
| TU campus | **11.1 (9.8–12.8)** | 10.0 (8.8–11.5) | 9.3 (8.2–10.7) |
| Voorhof | **14.4 (12.4–16.7)** | = technical | = technical |

One-at-a-time 5–95 % ranges (factor on the point estimate): weather year 0.97–1.14 (worst 2013, best 2022 — the TMY sits
near the dull end of 2005–2023), flat-roof layout 0.82–1.05 (Voorhof, 90 % flat) to 0.92–1.02 (Binnenstad), PR
0.94–1.06, trees 0.995–1.005, geometry 0.996–1.000 (σ ≤ 0.1 %). **Finding:** with 25 pts/m² AHN6 and validated
planes, geometric error is negligible for district totals; the weather year and the flat-roof layout assumption dominate.

## Web data export (web/public/data)

- `buurten.geojson` (0.13 MB): 76 CBS buurten with technical / permitted GWh, demand coverage, self-consumption with and
  without battery, value 2026 vs 2027, midday export peak, changes since 2023, CBS existing-PV share, AOI flag.
- `buildings.json` (2.7 MB): study-area buildings keyed by BAG id — roof area and kWh/m², shading and tree loss,
  kWp / kWh technical and permitted, demand, self-consumption, € 2026 / 2027 / 2027 + battery, heritage and change flags.
  CO₂ avoided is left empty: no sourced emission factor yet.
- `footprints.geojson` (2.5 MB): simplified study-area footprints (BAG id only) for click lookup and 2D layers.
- `tileset.json` + `tiles/*.glb` (48 MB in 16 files, 0.06–25 MB): 3D Tiles 1.1 with glTF content, one file per study
  area × AHN tile, local east-north-up metres, heights relative to each building's ground → sits on Cesium's ellipsoid
  without terrain; no Cesium ion token. Roofs coloured by our annual kWh/m² (inferno, 200–1200), walls grey.
- `cityjson/{binnenstad,campus,voorhof}.city.json` (30 / 7 / 8 MB): CityJSON 2.0, LoD2.2 MultiSurface in NAP
  (EPSG:7415) with RoofSurface / WallSurface / GroundSurface semantics; every roof surface carries plane id, slope,
  aspect and kWh/m²; buildings carry the attributes above.
- Geometry: roofs from our own planes (fragments < 4 m² merged for display only, outlines simplified 0.4 m, clipped
  to the BAG footprint); walls follow the roof height along the footprint (sampled 1 m, RDP 0.3 m).
- Checks: all glb files parse with valid indices; 1,158 sampled Binnenstad roof surfaces sit a median 0.10 m from the
  AHN6 DSM (89 % < 0.5 m); the tileset loads in CesiumJS 1.123 with no failed tiles, upright and aligned with OSM
  (`web/public/check-tiles.html` is a developer check page, not part of the site).

## Website (web/)

Vite 8 + vanilla TypeScript 7; CesiumJS 1.146, MapLibre GL 6.12, ECharts 6.1 (exact pins; all ≥ 3 weeks old).
Node.js 24.22.1 LTS installed per-user (`%LOCALAPPDATA%\Programs\node-v24.22.1-win-x64`, SHA-256 verified, on user PATH).

- **3D twin (hero):** self-hosted 3D Tiles (no Cesium ion token) over the PDOK aerial photo (dimmed); sun & shadow
  control (21 Mar/Jun/Sep/Dec, 06:00–21:00 Amsterdam time, DST-correct); fly-to per study area; PDOK Locatieserver
  address search; click a building → inspector (roof, shading and tree loss, kWp/kWh for the selected scenario, value
  2026 vs 2027 with/without battery, heritage and change flags) with a translucent highlight volume.
- **Scenario toggles:** technical / permitted with permit / permitted without permit, and a 5 kWh battery per dwelling —
  drive the headline cards, the dashboard and the inspector.
- **Neighbourhood dashboard:** MapLibre with CARTO dark-matter (vector), 21 study-area CBS buurten coloured by 8 metrics
  (yield, permitted share, demand covered, self-consumption, 2027 value change, export peak, CBS existing PV, new
  buildings); footprints coloured by roof kWh/m² from zoom 14.5; click → buurt card.
- **Science section:** pipeline diagram, validation cards, PVGIS scatter, uncertainty box plots and tornado, weather
  years, tree sensitivity, campus vs Zhou et al. steps, change statistics, results table; limitations, data & licences.
- **Numbers:** every value is read from `web/public/data/site.json` (+ buurten/buildings files), written by
  `python -m delft_twin.export` from the pipeline outputs. JSON is written with `allow_nan=False`.
- **Weight:** 3D Tiles compressed with meshopt (`npm run optimize-tiles`, 48.4 → 8.5 MB; centre tile 24.6 → 4.3 MB).
  Gzipped JS: Cesium module 1.1 MB, charts 0.38 MB, map 0.28 MB, sections lazy-loaded.
- **Deploy:** `.github/workflows/pages.yml` (npm ci → typecheck → build → GitHub Pages). `base: "./"` works under any
  sub-path. `?debug` exposes the viewer as `window.__twin` for inspection.

Fixes found while verifying in the browser: Cesium assets copied with their node_modules path (static-copy v4 keeps
structure → `stripBase: 4`); MapLibre 6's worker module imports `maplibre-gl-shared.mjs` (both copied, `setWorkerUrl`);
CARTO raster tiles now need an API key (→ PDOK aerial for the 3D base); requestRenderMode stopped refining imagery after
the camera flight (→ render until globe and tileset report loaded); `buildings.json` contained `NaN` (→ null).

## Risks and open items

- Website not yet in a git repository / on GitHub: create the repo, push, enable Pages (Settings → Pages → GitHub
  Actions). README with screenshots / demo GIF still to write.
- Author links (LinkedIn, GitHub) are not on the site yet — add them to the About card.
- AHN4/AHN5 swipe view (report idea) is represented by change classes and statistics, not a raster swipe.

- Heritage layer is indicative (rules from a 2019 report; municipal monuments missing; visibility approximated by a
  4 m rule and front-facing slopes rather than a true viewshed from street level).
- Demand is CBS grid delivery per dwelling (gross use is not published for 2024): a lower bound where PV is already
  common; mixed-use buildings count every verblijfsobject as a dwelling. Non-residential demand (campus) not modelled,
  and non-residential export is not in the buurt peaks.
- Hourly PV shape uses unobstructed POA scaled to each plane's shaded annual total (winter shading under-weighted in
  the hourly balance).
- Supplier feed-in costs (terugleverkosten) and capex/payback are not included (no sourced values yet).
- Campus comparison: ~30 % residual difference to Zhou et al. not attributed (their building list is not published).
- Shadow ring outside the 14 tiles uses the official AHN6 DSM, so trees there are treated as opaque.
- Roof cells on the boundary between two buildings owned by different tiles can be written twice; the city raster keeps
  the last one (affects only shared 0.5 m edge cells).
- Data budget: 14 AHN6 tiles = 3.4 GB LAZ + 12 reference CityJSON tiles; within the 5 GB target.
