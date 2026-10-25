// MapLibre neighbourhood dashboard: CBS buurten of the study areas, coloured by a chosen metric.
import { Map as MlMap, NavigationControl, Popup, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 loads its worker as a separate module that imports ./maplibre-gl-shared.mjs; both files are copied
// unchanged to <base>/maplibre/ by vite.config.ts
setWorkerUrl(new URL(import.meta.env.BASE_URL + "maplibre/maplibre-gl-worker.mjs", location.href).href);
import { AOI_LABEL, SCENARIO_LABEL, State, dataUrl, eur, infernoStops, legendGradient, load, num, onState, pct, signedPct, state } from "./data";

type P = Record<string, any>;
interface Metric { key: string; label: string; unit: string; value: (p: P, s: State) => number | null; fmt: (v: number | null) => string; ramp: "seq" | "div" }

const ratio = (a: number | null, b: number | null) => (a == null || !b ? null : a / b);
const scenGwh = (p: P, s: State) =>
  s.scenario === "technical" ? p.gwh : s.scenario === "permitted_incl_permit" ? p.gwh_permitted : p.gwh_nopermit;

const METRICS: Metric[] = [
  { key: "gwh", label: "Rooftop PV yield (GWh/yr)", unit: "GWh/yr", value: scenGwh, fmt: (v) => num(v, 2), ramp: "seq" },
  { key: "perm", label: "Share of technical potential allowed", unit: "", value: (p, s) => ratio(scenGwh(p, s), p.gwh),
    fmt: (v) => pct(v), ramp: "seq" },
  { key: "cov", label: "Home electricity covered by rooftop PV", unit: "", value: (p) => p.coverage, fmt: (v) => pct(v), ramp: "seq" },
  { key: "scr", label: "PV used on site (self-consumption)", unit: "", value: (p, s) => (s.battery ? p.scr_batt : p.scr),
    fmt: (v) => pct(v), ramp: "seq" },
  { key: "val", label: "Value change when net metering ends", unit: "",
    value: (p, s) => {
      const r = ratio(s.battery ? p.value_2027_batt_keur : p.value_2027_keur, p.value_2026_keur);
      return r == null ? null : r - 1;
    },
    fmt: (v) => signedPct(v), ramp: "div" },
  { key: "exp", label: "Midday export peak from homes (kW)", unit: "kW", value: (p) => p.export_peak_kw, fmt: (v) => num(v), ramp: "seq" },
  { key: "cbs", label: "Homes with solar panels today (CBS 2024)", unit: "%", value: (p) => p.cbs_pct_dwellings_with_pv,
    fmt: (v) => (v == null ? "–" : num(v) + " %"), ramp: "seq" },
  { key: "new", label: "New buildings since 2023 (AHN5 → AHN6)", unit: "", value: (p) => p.n_new, fmt: (v) => num(v), ramp: "seq" },
];
const SEQ = ["#1b2430", "#1f4a52", "#2a7a76", "#4fd1c5", "#b6f2ec"];
const DIV = ["#fc8181", "#f3b0a0", "#2a303b", "#9ae6b4", "#68d391"];

export async function initDashboard(mapEl: HTMLElement, select: HTMLSelectElement, card: HTMLElement, legend: HTMLElement, lede: HTMLElement) {
  const fc = await load<any>("buurten.geojson");
  fc.features = fc.features.filter((f: any) => f.properties.aoi);
  const site = await load<any>("site.json");
  lede.textContent = `${fc.features.length} CBS neighbourhoods in the three study areas. Values come from the per-building model aggregated per buurt; ` +
    `prices are the CBS average of ${site.prices.months.replace("..", " – ").replace(/MM/g, "-")}.`;

  select.innerHTML = METRICS.map((m) => `<option value="${m.key}">${m.label}</option>`).join("");
  const map = new MlMap({
    container: mapEl, style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    center: [4.3605, 52.0035], zoom: 12.6, attributionControl: { compact: true },
  });
  map.addControl(new NavigationControl({ showCompass: false }), "top-left");
  await new Promise<void>((r) => map.once("load", () => r()));

  map.addSource("buurten", { type: "geojson", data: fc, promoteId: "buurtcode" });
  map.addSource("fp", { type: "geojson", data: dataUrl("footprints.geojson") });
  map.addLayer({ id: "buurt-fill", type: "fill", source: "buurten", paint: { "fill-color": "#2a303b", "fill-opacity": 0.78 } });
  map.addLayer({ id: "buurt-line", type: "line", source: "buurten", paint: { "line-color": "#0e1014", "line-width": 1.2 } });
  map.addLayer({ id: "buurt-sel", type: "line", source: "buurten", paint: { "line-color": "#4fd1c5", "line-width": 2.5 },
    filter: ["==", ["get", "buurtcode"], ""] });
  const stops = infernoStops().flat();
  map.addLayer({ id: "fp", type: "fill", source: "fp", minzoom: 14.5,
    paint: { "fill-color": ["interpolate", ["linear"], ["coalesce", ["get", "k"], 0], ...stops], "fill-opacity": 0.95 } });

  const popup = new Popup({ closeButton: false, closeOnClick: false });
  let current = METRICS[0];
  let selected: string | null = null;

  const recolor = () => {
    const m = METRICS.find((x) => x.key === select.value) ?? METRICS[0];
    current = m;
    const vals: number[] = [];
    for (const f of fc.features) {
      const v = m.value(f.properties, state);
      f.properties._v = v;
      if (v != null && isFinite(v)) vals.push(v);
    }
    (map.getSource("buurten") as any).setData(fc);
    vals.sort((a, b) => a - b);
    let lo = vals[0] ?? 0, hi = vals[vals.length - 1] ?? 1;
    if (m.ramp === "div") { const a = Math.max(Math.abs(lo), Math.abs(hi)); lo = -a; hi = a; }
    if (hi === lo) hi = lo + 1;
    const pal = m.ramp === "div" ? DIV : SEQ;
    const expr: any[] = ["interpolate", ["linear"], ["to-number", ["get", "_v"]]];
    pal.forEach((c, i) => expr.push(lo + ((hi - lo) * i) / (pal.length - 1), c));
    map.setPaintProperty("buurt-fill", "fill-color", ["case", ["==", ["get", "_v"], null], "#20252e", expr] as any);
    legend.innerHTML = `${m.label}${m.key === "gwh" || m.key === "perm" ? ` · ${SCENARIO_LABEL[state.scenario]}` : ""}
      <div class="bar" style="background:linear-gradient(90deg,${pal.join(",")})"></div>
      <div class="ticks"><span>${m.fmt(lo)}</span><span>${m.fmt(hi)}</span></div>
      <div style="margin-top:6px">Buildings (zoom in): roof kWh/m²·yr</div>
      <div class="bar" style="background:${legendGradient()}"></div><div class="ticks"><span>200</span><span>1200</span></div>`;
    if (selected) showCard(selected);
  };

  const showCard = (code: string) => {
    const p = fc.features.find((f: any) => f.properties.buurtcode === code)?.properties;
    if (!p) return;
    const s = state;
    const row = (k: string, v: string) => `<div class="stat-row"><span>${k}</span><span>${v}</span></div>`;
    card.classList.remove("muted-card");
    card.innerHTML = `<div class="muted small">${AOI_LABEL[p.aoi as keyof typeof AOI_LABEL]}</div><h3>${p.buurtnaam}</h3>
      ${row("Buildings / dwellings", `${num(p.n_buildings)} / ${num(p.dwellings)}`)}
      ${row("PV yield, technical", `${num(p.gwh, 2)} GWh/yr`)}
      ${row("… permitted (with permit)", `${num(p.gwh_permitted, 2)} GWh/yr`)}
      ${row("… permitted (no permit)", `${num(p.gwh_nopermit, 2)} GWh/yr`)}
      ${row("Home electricity covered", pct(p.coverage))}
      ${row(`Used on site${s.battery ? " (battery)" : ""}`, pct(s.battery ? p.scr_batt : p.scr))}
      ${row("Value 2026 → 2027", `${eur(p.value_2026_keur * 1e3)} → ${eur((s.battery ? p.value_2027_batt_keur : p.value_2027_keur) * 1e3)}`)}
      ${row("Midday export peak", p.export_peak_kw == null ? "–" : `${num(p.export_peak_kw)} kW`)}
      ${row("Homes with PV today (CBS)", p.cbs_pct_dwellings_with_pv == null ? "–" : `${num(p.cbs_pct_dwellings_with_pv)} %`)}
      ${row("Protected / monuments", `${num(p.n_protected)} / ${num(p.n_monuments)}`)}
      ${row("New / raised since 2023", `${num(p.n_new)} / ${num(p.n_raised)}`)}`;
  };

  map.on("mousemove", "buurt-fill", (e) => {
    const p = e.features?.[0]?.properties;
    if (!p) return;
    map.getCanvas().style.cursor = "pointer";
    popup.setLngLat(e.lngLat).setHTML(`<b>${p.buurtnaam}</b><br>${current.fmt(p._v === "null" ? null : +p._v)}`).addTo(map);
  });
  map.on("mouseleave", "buurt-fill", () => { map.getCanvas().style.cursor = ""; popup.remove(); });
  map.on("click", "buurt-fill", (e) => {
    const code = e.features?.[0]?.properties?.buurtcode;
    if (!code) return;
    selected = code;
    map.setFilter("buurt-sel", ["==", ["get", "buurtcode"], code]);
    showCard(code);
  });
  select.addEventListener("change", recolor);
  onState(recolor);
  recolor();
}
