// Data loading, shared scenario state and formatting. Every number shown comes from data/*.json,
// which the Python pipeline writes from results/ — nothing is computed here beyond sums and ratios.

export type AoiKey = "binnenstad" | "campus" | "voorhof";
export const AOIS: AoiKey[] = ["binnenstad", "campus", "voorhof"];
export const AOI_LABEL: Record<AoiKey, string> = {
  binnenstad: "Binnenstad",
  campus: "TU Delft campus",
  voorhof: "Voorhof",
};

export interface Building {
  aoi: AoiKey; buurt: string; bouwjaar: number | null; h: number | null; use: string; dwellings: number;
  monument: boolean; protected_view: boolean; change: string | null;
  roof_m2: number | null; roof_kwh_m2: number | null; shading_loss: number | null; tree_loss: number | null;
  kwp: number | null; kwh: number | null; kwp_permitted: number | null; kwh_permitted: number | null; kwh_nopermit: number | null;
  demand_kwh: number | null; scr: number | null; scr_batt: number | null;
  eur_2026: number | null; eur_2027: number | null; eur_2027_batt: number | null;
}

export type Scenario = "technical" | "permitted_incl_permit" | "permitted_no_permit";
export const SCENARIO_LABEL: Record<Scenario, string> = {
  technical: "Technical potential",
  permitted_incl_permit: "Permitted (monuments with permit)",
  permitted_no_permit: "Permitted without permit",
};

export interface State { scenario: Scenario; battery: boolean }
const listeners: ((s: State) => void)[] = [];
export const state: State = { scenario: "technical", battery: false };
export function setState(p: Partial<State>) {
  Object.assign(state, p);
  listeners.forEach((f) => f(state));
}
export function onState(f: (s: State) => void) { listeners.push(f); }

const base = import.meta.env.BASE_URL + "data/";
const cache = new Map<string, Promise<any>>();
export function load<T = any>(name: string): Promise<T> {
  if (!cache.has(name)) cache.set(name, fetch(base + name).then((r) => {
    if (!r.ok) throw new Error(`${name}: ${r.status}`);
    return r.json();
  }));
  return cache.get(name)!;
}
export const dataUrl = (name: string) => base + name;

// ------------------------------------------------------------------ formatting
const nf = (d: number) => new Intl.NumberFormat("en-GB", { maximumFractionDigits: d, minimumFractionDigits: d });
export const num = (v: number | null | undefined, d = 0) => (v == null || !isFinite(v) ? "–" : nf(d).format(v));
export const pct = (v: number | null | undefined, d = 0) => (v == null || !isFinite(v) ? "–" : nf(d).format(100 * v) + " %");
export const signedPct = (v: number | null | undefined, d = 0) =>
  v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "−") + nf(d).format(Math.abs(100 * v)) + " %";
export const eur = (v: number | null | undefined) => (v == null || !isFinite(v) ? "–" : "€ " + nf(0).format(v));

// ------------------------------------------------------------------ solar colour ramp (inferno, as in the 3D tiles)
const INFERNO = ["#000004", "#1b0c41", "#4a0c6b", "#781c6d", "#a52c60", "#cf4446", "#ed6925", "#fb9b06", "#f7d13d", "#fcffa4"];
export const KWH_RANGE: [number, number] = [200, 1200];
export function infernoStops(lo = KWH_RANGE[0], hi = KWH_RANGE[1]): [number, string][] {
  return INFERNO.map((c, i) => [lo + ((hi - lo) * i) / (INFERNO.length - 1), c]);
}
export function legendGradient(): string {
  return `linear-gradient(90deg, ${INFERNO.join(",")})`;
}
