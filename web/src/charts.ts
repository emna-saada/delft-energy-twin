// Shared palette and ECharts setup. The same semantic colours are defined as CSS tokens in style.css;
// docs/DESIGN.md explains what each one stands for and lists its contrast ratio.
import * as echarts from "echarts";

export const C = {
  ink: "#16191D", ink2: "#454B54", ink3: "#646A73", rule: "#DAD5CB", paper: "#F7F5F0", surface: "#FFFFFF",
  delft: "#1F3F8F",      // Delft blue: identity, heritage, the historic centre
  solar: "#C96A08",      // solar production (fill); text uses solarInk
  solarInk: "#9A4A00",
  solarSoft: "#F3D3A6",
  winter: "#5B78B8",     // December / low sun
  home: "#2B6F60",       // power used at home (self-consumption)
  loss: "#A93E2C",       // value lost, not allowed, lowered
  permit: "#8A5D0B",     // needs a permit, raised / extended
  ok: "#37703F",         // allowed, new
  change: "#5E4590",     // AHN5 -> AHN6 change
  neutral: "#CFC9BD",    // unchanged / no data
};
export const AOI_COL: Record<string, string> = { binnenstad: C.delft, campus: "#0079A6", voorhof: "#5F6F24" };
// kept for older call sites
export const TXT = C.ink3, LINE = C.rule;

const FONT = "'Public Sans', system-ui, sans-serif";
const base = {
  backgroundColor: "transparent", textStyle: { color: C.ink2, fontFamily: FONT, fontSize: 12 },
  grid: { left: 56, right: 18, top: 40, bottom: 44 },
  tooltip: {
    trigger: "axis", backgroundColor: C.surface, borderColor: C.rule, borderWidth: 1, padding: [8, 10],
    textStyle: { color: C.ink, fontFamily: FONT, fontSize: 12 }, extraCssText: "box-shadow:none;border-radius:2px",
  },
  legend: { textStyle: { color: C.ink2 }, top: 4, left: 0, icon: "rect", itemWidth: 12, itemHeight: 8 },
};

export const axis = (name: string, extra: object = {}) => ({
  name, nameLocation: "middle", nameGap: 32, nameTextStyle: { color: C.ink3, fontSize: 11 },
  axisLine: { show: false }, axisTick: { show: false },
  splitLine: { lineStyle: { color: C.rule, type: [2, 3] } }, axisLabel: { color: C.ink3 }, ...extra,
});

export const catAxis = (data: (string | number)[], extra: object = {}) => ({
  type: "category", data, axisLabel: { color: C.ink3 }, axisTick: { show: false },
  axisLine: { lineStyle: { color: C.ink2 } }, ...extra,
});

export function chart(el: HTMLElement, opt: any) {
  const c = echarts.init(el, undefined, { renderer: "canvas" });
  c.setOption({ ...base, ...opt });
  new ResizeObserver(() => c.resize()).observe(el);
  return c;
}
