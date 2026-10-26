// Shared ECharts setup for the dark theme.
import * as echarts from "echarts";

export const TXT = "#9aa3ae", LINE = "#2a303b", ACC = "#4fd1c5", SUN = "#f6ad55";
export const AOI_COL: Record<string, string> = { binnenstad: "#f6ad55", campus: "#4fd1c5", voorhof: "#b794f4" };

const base = {
  backgroundColor: "transparent", textStyle: { color: TXT, fontFamily: "Inter, system-ui, sans-serif" },
  grid: { left: 56, right: 18, top: 36, bottom: 44 },
  tooltip: { trigger: "axis", backgroundColor: "#161a22", borderColor: LINE, textStyle: { color: "#eceef1" } },
  legend: { textStyle: { color: TXT }, top: 4 },
};

export const axis = (name: string, extra: object = {}) => ({
  name, nameLocation: "middle", nameGap: 32, nameTextStyle: { color: TXT },
  axisLine: { lineStyle: { color: LINE } }, splitLine: { lineStyle: { color: LINE } }, axisLabel: { color: TXT }, ...extra,
});

export const catAxis = (data: (string | number)[], extra: object = {}) => ({
  type: "category", data, axisLabel: { color: TXT }, axisLine: { lineStyle: { color: LINE } }, ...extra,
});

export function chart(el: HTMLElement, opt: any) {
  const c = echarts.init(el, undefined, { renderer: "canvas" });
  c.setOption({ ...base, ...opt });
  new ResizeObserver(() => c.resize()).observe(el);
  return c;
}
