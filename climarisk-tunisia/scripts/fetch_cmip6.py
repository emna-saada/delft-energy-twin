"""Stream NASA NEX-GDDP-CMIP6 daily files from AWS Open Data and keep only
Tunisia-wide annual indicators (no AWS account needed, unsigned HTTPS).

Output: data/raw/cmip6/<model>_<scenario>_<year>.nc with variables
  hot35   days with tasmax > 35 °C
  hot40   days with tasmax > 40 °C
  prtot   annual precipitation (mm)
  cdd     max consecutive dry days (pr < 1 mm)
  prmon   monthly precipitation (mm), dim month

Usage: python scripts/fetch_cmip6.py [--workers 8]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import re
import subprocess
import tempfile
import sys
import time
from pathlib import Path

import numpy as np
import requests
import xarray as xr
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://nex-gddp-cmip6.s3.us-west-2.amazonaws.com"
BBOX = dict(lat=slice(30.0, 37.75), lon=slice(7.25, 11.75))


def list_keys(prefix: str) -> list[str]:
    keys, token = [], None
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if token:
            params["continuation-token"] = token
        r = requests.get(BASE + "/", params=params, timeout=60)
        r.raise_for_status()
        keys += re.findall(r"<Key>([^<]+)</Key>", r.text)
        m = re.search(r"<NextContinuationToken>([^<]+)<", r.text)
        if not m:
            return keys
        token = m.group(1)


def pick_file(keys: list[str], year: int) -> str | None:
    cands = [k for k in keys if k.endswith(f"_{year}.nc") or k.endswith(f"_{year}_v2.0.nc")]
    v2 = [k for k in cands if "_v2.0" in k]
    return (v2 or cands or [None])[0]


def subset(url: str, var: str) -> xr.DataArray:
    """Download the global daily file with curl (much faster than HTTP range reads
    because chunks are full global days), cut Tunisia, delete the file."""
    tmp = Path(tempfile.gettempdir()) / ("cmip6_" + url.rsplit("/", 1)[-1])
    for attempt in range(4):
        try:
            subprocess.run(["curl", "-sSf", "--retry", "3", "-o", str(tmp), url], check=True)
            with xr.open_dataset(tmp, engine="h5netcdf") as ds:
                return ds[var].sel(**BBOX).load()
        except Exception as e:  # network hiccups
            print(f"retry {attempt} {url}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
        finally:
            tmp.unlink(missing_ok=True)
    raise RuntimeError(url)


def max_run(mask: np.ndarray) -> np.ndarray:
    """Longest run of True along axis 0."""
    best = np.zeros(mask.shape[1:], dtype=np.int16)
    cur = np.zeros_like(best)
    for d in mask:
        cur = np.where(d, cur + 1, 0)
        best = np.maximum(best, cur)
    return best


def job(model: str, member: str, scen: str, year: int, keys_cache: dict) -> str:
    out = ROOT / f"data/raw/cmip6/{model}_{scen}_{year}.nc"
    if out.exists():
        return f"skip {out.name}"
    res = {}
    for var in ("tasmax", "pr"):
        key = pick_file(keys_cache[(model, scen, var)], year)
        if key is None:
            return f"MISSING {model} {scen} {var} {year}"
        da = subset(f"{BASE}/{key}", var)
        if var == "tasmax":
            t = da.values - 273.15
            res["hot35"] = (t > 35).sum(0)
            res["hot40"] = (t > 40).sum(0)
        else:
            p = da.values * 86400.0  # kg m-2 s-1 -> mm/day
            res["prtot"] = p.sum(0)
            res["cdd"] = max_run(p < 1.0)
            months = da["time"].dt.month.values
            res["prmon"] = np.stack([p[months == m].sum(0) for m in range(1, 13)])
        lat, lon = da.lat.values, da.lon.values
    ds = xr.Dataset(
        {k: (("month", "lat", "lon") if k == "prmon" else ("lat", "lon"), v) for k, v in res.items()},
        coords={"lat": lat, "lon": lon, "month": np.arange(1, 13)},
        attrs={"model": model, "scenario": scen, "year": year, "source": "NASA NEX-GDDP-CMIP6 (AWS Open Data)"},
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out)
    return f"done {out.name}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "config/scenarios.yaml"))
    tasks, cache = [], {}
    for m in cfg["cmip6_models"]:
        model, member = m["name"], m["member"]
        for scen, years in cfg["years"].items():
            for var in ("tasmax", "pr"):
                cache[(model, scen, var)] = list_keys(f"NEX-GDDP-CMIP6/{model}/{scen}/{member}/{var}/")
            for y in years:
                tasks.append((model, member, scen, y))
    print(f"{len(tasks)} model-scenario-years to process", flush=True)
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(job, *t, cache) for t in tasks]
        for i, fu in enumerate(cf.as_completed(futs), 1):
            try:
                print(f"[{i}/{len(tasks)}] {fu.result()}", flush=True)
            except Exception as e:
                print(f"[{i}/{len(tasks)}] FAILED {e}", flush=True)


if __name__ == "__main__":
    main()
