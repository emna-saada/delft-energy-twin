"""Download small static open datasets: governorate boundaries, population, coastline."""
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
FILES = {
    # geoBoundaries gbOpen TUN ADM1 (ODbL 1.0, source OpenStreetMap/Wambacher), pinned commit
    "tun_adm1.geojson": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/"
                        "releaseData/gbOpen/TUN/ADM1/geoBoundaries-TUN-ADM1_simplified.geojson",
    # WorldPop 2020, 1 km, UN-adjusted (CC BY 4.0)
    "worldpop_tun_2020_1km.tif": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/"
                                 "2020/TUN/tun_ppp_2020_1km_Aggregated_UNadj.tif",
    # Natural Earth 1:10m coastline (public domain)
    "ne_coast.zip": "https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_coastline.zip",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        out = RAW / name
        if out.exists():
            print("skip", name)
            continue
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        out.write_bytes(r.content)
        print("got", name, len(r.content))
