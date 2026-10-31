// MapLibre map explorer: CBS buurten of the study areas coloured by a chosen metric, plus a buildings layer.
import { Map as MlMap, NavigationControl, Popup, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 loads its worker as a separate module that imports ./maplibre-gl-shared.mjs; both files are copied
// unchanged to <base>/maplibre/ by vite.config.ts
setWorkerUrl(new URL(import.meta.env.BASE_URL + "maplibre/maplibre-gl-worker.mjs", location.href).href);
import { AOI_LABEL, SCENARIO_LABEL, State, dataUrl, eur, infernoStops, legendGradient, load, num, onState, pct, signedPct, state } from "./data";
import { C } from "./charts";

type P = Record<string, any>;
interface Metric {
  key: string; chip: string; label: string; help: string;
  value: (p: P, s: State) => number | null; fmt: (v: number | null) => string; ramp: "seq" | "div";
}

const ratio = (a: number | null, b: number | null) => (a == null || !b ? null : a / b);
const scenGwh = (p: P, s: State) =>
  s.scenario === "technical" ? p.gwh : s.scenario === "permitted_incl_permit" ? p.gwh_permitted : p.gwh_nopermit;

const METRICS: Metric[] = [
  { key: "gwh", chip: "Solar yield", label: "Rooftop solar yield (GWh/yr)", ramp: "seq", value: scenGwh, fmt: (v) => num(v, 2),
    help: "Total yearly electricity all suitable roofs in the neighbourhood could produce, for the scenario chosen in the 3D view. Big flat-roofed areas (the campus) score highest." },
  { key: "perm", chip: "Allowed share", label: "Share of technical potential allowed", ramp: "seq", fmt: (v) => pct(v),
    value: (p, s) => ratio(scenGwh(p, s), p.gwh),
    help: "How much of the technical potential survives the heritage rules. Choose a “permitted” scenario in the 3D view (step 1) — in the historic centre it drops well below 100 %." },
  { key: "cov", chip: "Demand covered", label: "Home electricity covered by rooftop solar", ramp: "seq", value: (p) => p.coverage, fmt: (v) => pct(v),
    help: "Yearly solar production on homes divided by the homes' yearly electricity use (CBS). Over 100 % means the roofs could produce more than the homes use — over a year, not every hour." },
  { key: "scr", chip: "Used at home", label: "Solar power used at home (self-consumption)", ramp: "seq", fmt: (v) => pct(v),
    value: (p, s) => (s.battery ? p.scr_batt : p.scr),
    help: "Share of solar power consumed in the same hour it is produced. After 2027 this is what pays. Tick the home battery in the 3D view to see how much a 5 kWh battery adds." },
  { key: "val", chip: "2027 value change", label: "Value change when net metering ends", ramp: "div", fmt: (v) => signedPct(v),
    value: (p, s) => { const r = ratio(s.battery ? p.value_2027_batt_keur : p.value_2027_keur, p.value_2026_keur); return r == null ? null : r - 1; },
    help: "How much the yearly value of home solar panels changes on 1 January 2027, when exported power is no longer netted. Every neighbourhood loses; homes that use more of their own power lose less." },
  { key: "exp", chip: "Grid export peak", label: "Midday export peak from homes (kW)", ramp: "seq", value: (p) => p.export_peak_kw, fmt: (v) => num(v),
    help: "The highest hourly surplus that homes in the neighbourhood push into the grid in the typical year — a pointer to where local grid congestion may appear." },
  { key: "cbs", chip: "Panels today", label: "Homes with solar panels today (CBS 2024)", ramp: "seq", value: (p) => p.cbs_pct_dwellings_with_pv,
    fmt: (v) => (v == null ? "–" : num(v) + " %"),
    help: "Official CBS statistic: share of homes that already have solar panels. Compare with the potential to see where most room is left." },
  { key: "new", chip: "New buildings", label: "New buildings since 2023 (AHN5 → AHN6)", ramp: "seq", value: (p) => p.n_new, fmt: (v) => num(v),
    help: "Buildings that did not exist in the 2023 laser scan but do in the 2025/26 scan." },
];

interface BldMode { key: string; chip: string; help: string; paint: any; legend: string }
const CHANGE_COL: [string, string, string][] = [["new_since_2023", C.ok, "new since 2023"], ["raised_or_extended", C.permit, "raised / extended"],
  ["lowered", C.loss, "lowered"], ["unchanged", C.neutral, "unchanged"]];
const NO_ROOF = "#E4DFD5";
const BLD_MODES: BldMode[] = [
  { key: "off", chip: "Off", help: "Buildings hidden — only neighbourhoods are shown.", paint: null, legend: "" },
  { key: "sun", chip: "Roof sun", help: "Each building coloured by the average yearly sun on its roof, after shading — the same colours as the 3D view.",
    paint: ["interpolate", ["linear"], ["coalesce", ["get", "k"], 0], ...infernoStops().flat()],
    legend: `<b>Buildings</b> · roof sun (kWh/m²·yr)<div class="bar" style="background:${legendGradient()}"></div><div class="ticks"><span>200</span><span>1200</span></div>` },
  { key: "heritage", chip: "Heritage", help: "Share of each building's solar potential that the indicative heritage rules allow: red = none, green = all. Grey = no usable roof.",
    paint: ["case", ["==", ["get", "p"], null], NO_ROOF, ["interpolate", ["linear"], ["get", "p"], 0, C.loss, 0.5, "#D9A441", 1, C.ok]],
    legend: `<b>Buildings</b> · share allowed by heritage rules<div class="bar" style="background:linear-gradient(90deg,${C.loss},#D9A441,${C.ok})"></div><div class="ticks"><span>0 %</span><span>100 %</span></div>` },
  { key: "monument", chip: "Monuments", help: "National monuments (rijksmonumenten, RCE) — panels need an individual permit.",
    paint: ["case", ["==", ["get", "m"], 1], C.delft, "#D3CDC1"],
    legend: `<b>Buildings</b><div class="cats"><span><i style="background:${C.delft}"></i>national monument</span><span><i style="background:#D3CDC1"></i>other</span></div>` },
  { key: "change", chip: "Change 2023→26", help: "What changed between the 2023 and 2025/26 laser scans.",
    paint: ["match", ["get", "c"], ...CHANGE_COL.slice(0, 3).flatMap(([k, c]) => [k, c]), CHANGE_COL[3][1]],
    legend: `<b>Buildings</b><div class="cats">${CHANGE_COL.map(([, c, l]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}</div>` },
];
// sequential: Delft blue, light to dark; diverging: loss (brick) - neutral - gain (green)
const SEQ = ["#EEF1F7", "#C3CFE8", "#8BA1D2", "#4E6CB3", "#1F3F8F", "#12275A"];
const DIV = [C.loss, "#D99A8C", "#F1EDE5", "#9DC2A3", C.ok];

export async function initDashboard(mapEl: HTMLElement, metricChips: HTMLElement, metricHelp: HTMLElement, bldChips: HTMLElement,
  bldHelp: HTMLElement, card: HTMLElement, legend: HTMLElement, lede: HTMLElement) {
  const fc = await load<any>("buurten.geojson");
  fc.features = fc.features.filter((f: any) => f.properties.aoi);
  lede.innerHTML = `The ${fc.features.length} CBS neighbourhoods of the three study areas. <b>Step 1</b> colours them by a measure,
    <b>step 2</b> adds every building on top, <b>step 3</b> shows one neighbourhood's numbers. Scenario and battery choices from the 3D view apply here too.`;

  metricChips.innerHTML = METRICS.map((m, i) => `<button data-k="${m.key}" aria-pressed="${i === 0}">${m.chip}</button>`).join("");
  bldChips.innerHTML = BLD_MODES.map((m) => `<button data-k="${m.key}" aria-pressed="${m.key === "sun"}">${m.chip}</button>`).join("");

  const map = new MlMap({
    container: mapEl, style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    center: [4.3605, 52.0035], zoom: 12.6, attributionControl: { compact: true },
  });
  map.addControl(new NavigationControl({ showCompass: false }), "top-left");
  await new Promise<void>((r) => map.once("load", () => r()));

  map.addSource("buurten", { type: "geojson", data: fc, promoteId: "buurtcode" });
  map.addSource("fp", { type: "geojson", data: dataUrl("footprints.geojson") });
  map.addLayer({ id: "buurt-fill", type: "fill", source: "buurten", paint: { "fill-color": SEQ[0], "fill-opacity": 0.85 } });
  map.addLayer({ id: "buurt-line", type: "line", source: "buurten", paint: { "line-color": "#ffffff", "line-width": 1.2 } });
  map.addLayer({ id: "fp", type: "fill", source: "fp", minzoom: 13.5, paint: { "fill-color": NO_ROOF, "fill-opacity": 0.95 } });
  map.addLayer({ id: "buurt-sel", type: "line", source: "buurten", paint: { "line-color": C.ink, "line-width": 2.5 },
    filter: ["==", ["get", "buurtcode"], ""] });

  const popup = new Popup({ closeButton: false, closeOnClick: false });
  let current = METRICS[0], bld = BLD_MODES[1];
  let selected: string | null = null;

  const renderLegend = (lo: number, hi: number, pal: string[]) => {
    legend.innerHTML = `<b>Neighbourhoods</b> · ${current.label}${current.key === "gwh" || current.key === "perm" ? ` · ${SCENARIO_LABEL[state.scenario]}` : ""}
      <div class="bar" style="background:linear-gradient(90deg,${pal.join(",")})"></div>
      <div class="ticks"><span>${current.fmt(lo)}</span><span>${current.fmt(hi)}</span></div>
      ${bld.legend ? `<div style="margin-top:8px">${bld.legend}${map.getZoom() < 13.5 ? `<div class="small">zoom in to see buildings</div>` : ""}</div>` : ""}`;
  };
  let lastLegend: [number, number, string[]] = [0, 1, SEQ];

  const recolor = () => {
    const vals: number[] = [];
    for (const f of fc.features) {
      const v = current.value(f.properties, state);
      f.properties._v = v;
      if (v != null && isFinite(v)) vals.push(v);
    }
    (map.getSource("buurten") as any).setData(fc);
    vals.sort((a, b) => a - b);
    let lo = vals[0] ?? 0, hi = vals[vals.length - 1] ?? 1;
    if (current.ramp === "div") { const a = Math.max(Math.abs(lo), Math.abs(hi)); lo = -a; hi = a; }
    if (hi === lo) hi = lo + 1;
    const pal = current.ramp === "div" ? DIV : SEQ;
    const expr: any[] = ["interpolate", ["linear"], ["to-number", ["get", "_v"]]];
    pal.forEach((c, i) => expr.push(lo + ((hi - lo) * i) / (pal.length - 1), c));
    map.setPaintProperty("buurt-fill", "fill-color", ["case", ["==", ["get", "_v"], null], NO_ROOF, expr] as any);
    metricHelp.textContent = current.help;
    lastLegend = [lo, hi, pal];
    renderLegend(lo, hi, pal);
    if (selected) showCard(selected);
  };

  const setBuildings = () => {
    map.setLayoutProperty("fp", "visibility", bld.paint ? "visible" : "none");
    if (bld.paint) map.setPaintProperty("fp", "fill-color", bld.paint);
    // buildings drawn on top: fade the neighbourhood colours so both read
    map.setPaintProperty("buurt-fill", "fill-opacity", bld.paint ? ["interpolate", ["linear"], ["zoom"], 13, 0.85, 14.5, 0.3] : 0.85);
    bldHelp.textContent = bld.help;
    renderLegend(...lastLegend);
  };

  const showCard = (code: string) => {
    const p = fc.features.find((f: any) => f.properties.buurtcode === code)?.properties;
    if (!p) return;
    const s = state;
    const row = (k: string, v: string) => `<div class="stat-row"><span>${k}</span><span>${v}</span></div>`;
    card.classList.remove("muted-card");
    card.innerHTML = `<div class="muted small">${AOI_LABEL[p.aoi as keyof typeof AOI_LABEL]}</div><h3>${p.buurtnaam}</h3>
      ${row("Buildings / dwellings", `${num(p.n_buildings)} / ${num(p.dwellings)}`)}
      ${row("Solar yield, technical", `${num(p.gwh, 2)} GWh/yr`)}
      ${row("… allowed (with permit)", `${num(p.gwh_permitted, 2)} GWh/yr`)}
      ${row("… allowed (no permit)", `${num(p.gwh_nopermit, 2)} GWh/yr`)}
      ${row("Home electricity covered", pct(p.coverage))}
      ${row(`Used at home${s.battery ? " (battery)" : ""}`, pct(s.battery ? p.scr_batt : p.scr))}
      ${row("Value 2026 → 2027", `${eur(p.value_2026_keur * 1e3)} → ${eur((s.battery ? p.value_2027_batt_keur : p.value_2027_keur) * 1e3)}`)}
      ${row("Midday export peak", p.export_peak_kw == null ? "–" : `${num(p.export_peak_kw)} kW`)}
      ${row("Homes with panels today (CBS)", p.cbs_pct_dwellings_with_pv == null ? "–" : `${num(p.cbs_pct_dwellings_with_pv)} %`)}
      ${row("Protected / monuments", `${num(p.n_protected)} / ${num(p.n_monuments)}`)}
      ${row("New / raised since 2023", `${num(p.n_new)} / ${num(p.n_raised)}`)}`;
  };

  map.on("mousemove", "buurt-fill", (e) => {
    const p = e.features?.[0]?.properties;
    if (!p) return;
    map.getCanvas().style.cursor = "pointer";
    popup.setLngLat(e.lngLat).setHTML(`<b>${p.buurtnaam}</b><br>${current.chip}: ${current.fmt(p._v === "null" ? null : +p._v)}`).addTo(map);
  });
  map.on("mouseleave", "buurt-fill", () => { map.getCanvas().style.cursor = ""; popup.remove(); });
  map.on("click", "buurt-fill", (e) => {
    const code = e.features?.[0]?.properties?.buurtcode;
    if (!code) return;
    selected = code;
    map.setFilter("buurt-sel", ["==", ["get", "buurtcode"], code]);
    showCard(code);
  });
  map.on("zoomend", () => renderLegend(...lastLegend));

  metricChips.querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.addEventListener("click", () => {
    metricChips.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    current = METRICS.find((m) => m.key === b.dataset.k)!;
    recolor();
  }));
  bldChips.querySelectorAll<HTMLButtonElement>("button").forEach((b) => b.addEventListener("click", () => {
    bldChips.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    bld = BLD_MODES.find((m) => m.key === b.dataset.k)!;
    setBuildings();
    if (bld.paint && map.getZoom() < 13.5) map.easeTo({ center: [4.3575, 52.0105], zoom: 14.6, duration: 900 });
  }));
  onState(recolor);
  recolor();
  setBuildings();
}
