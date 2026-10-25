// Building lookup (point-in-footprint), PDOK address search and the inspector panel.
import { AOI_LABEL, Building, SCENARIO_LABEL, State, eur, load, num, pct, signedPct, state } from "./data";

type Ring = number[][];
interface Footprint { id: string; rings: Ring[]; bbox: [number, number, number, number] }

const CELL = 0.002; // degrees, grid bucket size
let index: Map<string, Footprint[]> | null = null;
let indexPromise: Promise<void> | null = null;

export function ensureIndex(): Promise<void> {
  if (!indexPromise) {
    indexPromise = load<any>("footprints.geojson").then((fc) => {
      index = new Map();
      for (const f of fc.features) {
        const polys: Ring[][] = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
        for (const rings of polys) {
          const xs = rings[0].map((p) => p[0]), ys = rings[0].map((p) => p[1]);
          const fp: Footprint = { id: f.properties.identificatie, rings,
            bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
          for (let gx = Math.floor(fp.bbox[0] / CELL); gx <= Math.floor(fp.bbox[2] / CELL); gx++)
            for (let gy = Math.floor(fp.bbox[1] / CELL); gy <= Math.floor(fp.bbox[3] / CELL); gy++) {
              const k = `${gx}:${gy}`;
              if (!index.has(k)) index.set(k, []);
              index.get(k)!.push(fp);
            }
        }
      }
    });
  }
  return indexPromise;
}

function inRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export async function buildingAt(lon: number, lat: number): Promise<Footprint | null> {
  await ensureIndex();
  const cand = index!.get(`${Math.floor(lon / CELL)}:${Math.floor(lat / CELL)}`) || [];
  for (const f of cand) {
    if (lon < f.bbox[0] || lon > f.bbox[2] || lat < f.bbox[1] || lat > f.bbox[3]) continue;
    if (inRing(lon, lat, f.rings[0]) && !f.rings.slice(1).some((h) => inRing(lon, lat, h))) return f;
  }
  return null;
}

export const buildings = () => load<Record<string, Building>>("buildings.json");

// ------------------------------------------------------------------ PDOK Locatieserver
export interface Hit { label: string; lon: number; lat: number }
export async function searchAddress(q: string): Promise<Hit[]> {
  const url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?rows=6&fq=type:adres&fq=gemeentenaam:Delft&q=" +
    encodeURIComponent(q);
  const r = await fetch(url);
  if (!r.ok) return [];
  const j = await r.json();
  return (j.response?.docs ?? []).flatMap((d: any) => {
    const m = /POINT\(([-\d.]+) ([-\d.]+)\)/.exec(d.centroide_ll ?? "");
    return m ? [{ label: d.weergavenaam, lon: +m[1], lat: +m[2] }] : [];
  });
}

// ------------------------------------------------------------------ panel
const CHANGE_LABEL: Record<string, string> = {
  new_since_2023: "new since 2023", raised_or_extended: "raised / extended since 2023", lowered: "lowered since 2023",
};

function scenarioKwh(b: Building, s: State): [number | null, number | null] {
  if (s.scenario === "technical") return [b.kwp, b.kwh];
  if (s.scenario === "permitted_incl_permit") return [b.kwp_permitted, b.kwh_permitted];
  return [null, b.kwh_nopermit];
}

export function renderInspector(el: HTMLElement, id: string, b: Building | undefined, onClose: () => void) {
  el.hidden = false;
  if (!b) {
    el.innerHTML = `<button class="close" aria-label="Close">×</button>
      <h3>Building ${id}</h3><p class="muted">Outside the three study areas — no results exported for it.</p>`;
    el.querySelector(".close")!.addEventListener("click", onClose);
    return;
  }
  const s = state;
  const [kwp, kwh] = scenarioKwh(b, s);
  const tags = [
    b.monument ? `<span class="tag warn">rijksmonument · permit required</span>` : "",
    b.protected_view ? `<span class="tag warn">protected cityscape</span>` : "",
    b.change && CHANGE_LABEL[b.change] ? `<span class="tag good">${CHANGE_LABEL[b.change]}</span>` : "",
    b.dwellings > 0 ? `<span class="tag">${b.dwellings} dwelling${b.dwellings > 1 ? "s" : ""}</span>` : `<span class="tag">no dwellings</span>`,
  ].join("");
  const eur27 = s.battery ? b.eur_2027_batt : b.eur_2027;
  const scr = s.battery ? b.scr_batt : b.scr;
  const econ = b.eur_2026 != null
    ? `<div class="sub">Value of the panels on this building · technical layout</div>
       <div class="vs">
         <div><div class="lbl">2026 · net metering</div><div class="big">${eur(b.eur_2026)}</div><div class="lbl">per year</div></div>
         <div><div class="lbl">2027 rules${s.battery ? " + battery" : ""}</div><div class="big">${eur(eur27)}</div>
           <div class="lbl">${signedPct(eur27 != null && b.eur_2026 ? eur27 / b.eur_2026 - 1 : null)}</div></div>
       </div>
       <dl class="kv" style="margin-top:8px">
         <dt>Used on site${s.battery ? " (with battery)" : ""}</dt><dd>${pct(scr)}</dd>
         <dt>Home demand covered</dt><dd>${pct(b.kwh != null && b.demand_kwh ? b.kwh / b.demand_kwh : null)}</dd>
       </dl>`
    : `<p class="muted small" style="margin-top:10px">No household demand modelled for this building (no dwellings), so no value is shown.</p>`;
  el.innerHTML = `<button class="close" aria-label="Close">×</button>
    <div class="muted small">${AOI_LABEL[b.aoi]} · ${b.buurt ?? ""}</div>
    <h3>${b.use ? b.use.split(",")[0] : "building"}${b.bouwjaar ? ` · ${b.bouwjaar}` : ""}</h3>
    <div class="muted small">BAG ${id}</div>
    <div class="tags">${tags}</div>
    <div class="sub">Roof</div>
    <dl class="kv">
      <dt>Sky-visible roof</dt><dd>${num(b.roof_m2)} m²</dd>
      <dt>Mean sun on roof</dt><dd>${num(b.roof_kwh_m2)} kWh/m²·yr</dd>
      <dt>Lost to shading</dt><dd>${pct(b.shading_loss)}</dd>
      <dt>… of which trees</dt><dd>${pct(b.tree_loss, 1)}</dd>
    </dl>
    <div class="sub">${SCENARIO_LABEL[s.scenario]}</div>
    <dl class="kv">
      ${kwp != null ? `<dt>Panels</dt><dd>${num(kwp, 1)} kWp</dd>` : ""}
      <dt>Yield</dt><dd>${num(kwh)} kWh/yr</dd>
      ${s.scenario !== "technical" ? `<dt>Share of technical</dt><dd>${pct(kwh != null && b.kwh ? kwh / b.kwh : null)}</dd>` : ""}
    </dl>
    ${econ}
    <p class="muted small" style="margin-top:10px">Heritage status is indicative; tree shading uses leaf-off LiDAR (see method).</p>`;
  el.querySelector(".close")!.addEventListener("click", onClose);
}
