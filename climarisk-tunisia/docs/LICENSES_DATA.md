# Licences — data and software

Project code: **MIT**. No dataset is redistributed in the repository (only tiny synthetic test fixtures);
`make data` downloads everything from the original open sources.

## Datasets

| Dataset | Use | Access | Licence | Attribution required |
|---|---|---|---|---|
| NASA NEX-GDDP-CMIP6 (ACCESS-CM2, CNRM-ESM2-1, MPI-ESM1-2-HR, MRI-ESM2-0, IPSL-CM6A-LR) | Heat (Tmax > 35 °C days), drought (CDD, precipitation change) | AWS Open Data `s3://nex-gddp-cmip6`, unsigned HTTPS | Per model; NASA's technical note lists CC BY 4.0 for these five models (some other models are CC0 / CC BY-SA). **Re-check per model in the NEX-GDDP-CMIP6 technical note before publication.** | Yes — "NASA Earth Exchange Global Daily Downscaled Projections (NEX-GDDP-CMIP6)" + model institutions |
| WRI Aqueduct Floods v2 (riverine & coastal, RP 2–1000) | Flood depth | OS-Climate physrisk public Zarr, `s3://os-climate-physical-risk` | CC BY 4.0 | Yes — Ward et al. / WRI Aqueduct Floods |
| ESA WorldCover 10 m 2021 v200 | Wildfire fuel, cropland locations | AWS Open Data `s3://esa-worldcover` | CC BY 4.0 | Yes — "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)" |
| WorldPop 2020 1 km UN-adjusted | Location of synthetic loans | data.worldpop.org | CC BY 4.0 | Yes — WorldPop (www.worldpop.org) |
| geoBoundaries gbOpen TUN ADM1 | Governorate boundaries | GitHub release (pinned commit 9469f09) | ODbL 1.0 (source OpenStreetMap / Wambacher) — as reported by the geoBoundaries API | Yes — "© OpenStreetMap contributors, geoBoundaries" |
| Natural Earth 1:10m coastline | Coastal buffer | naturalearth.s3.amazonaws.com | Public domain | No (courtesy credit given) |
| OS-Climate physrisk hazard indicators (OSC chronic heat v2, OSC drought v2) | Comparison only (milestone 6) | `s3://os-climate-physical-risk` | Distributed with the Apache-2.0 physrisk project; dataset-level terms to re-check | Yes — OS-Climate |
| CARTO basemap (dashboard) | Background map tiles | pydeck "light" style | CARTO free tier terms for non-commercial use; © OpenStreetMap contributors | Yes |

Not used (and why): ERA5-Land (needs a CDS account → replaced by the NEX-GDDP historical run), CHIRPS / MODIS MCD64A1 (planned through Earth Engine Community tier once Emna authenticates), CLIMADA (GPL-3.0, optional and not installed).

## Software (main dependencies)

| Library | Licence |
|---|---|
| numpy, pandas, scipy, xarray, matplotlib | BSD-3-Clause (matplotlib: PSF-based) |
| geopandas, shapely, pyproj, rasterio | BSD-3-Clause / BSD |
| zarr, fsspec, h5netcdf, h5py | MIT / BSD-3-Clause |
| streamlit, pydeck | Apache-2.0 |
| plotly | MIT |
| jinja2 | BSD-3-Clause |
| weasyprint | BSD-3-Clause |
| playwright (dashboard capture) | Apache-2.0 |
| Remotion (video) | Remotion License — free for individuals and teams ≤ 3 people (FAQ checked 2026-11-20) |
| ffmpeg | LGPL-2.1+ (system binary, not redistributed) |
| Fira Sans / Fira Code fonts | SIL Open Font License 1.1 |
