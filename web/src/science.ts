// Method, validation, uncertainty and credits — every value read from data/site.json.
import { ACC, AOI_COL, LINE, TXT, axis, chart } from "./charts";
import { AOI_LABEL, AOIS, num, pct, signedPct } from "./data";

const PIPELINE = `<svg viewBox="0 0 1040 250" role="img" aria-label="Processing pipeline">
  <defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="#9aa3ae"/></marker></defs>
  <style>.b{fill:#161a21;stroke:#2a303b}.a{fill:#13302d;stroke:#4fd1c5}.t{fill:#e7e9ec;font:600 13px Inter,sans-serif}
    .s{fill:#9aa3ae;font:11px Inter,sans-serif}.l{stroke:#9aa3ae;stroke-width:1.4;fill:none;marker-end:url(#ar)}</style>
  ${[["AHN6 LiDAR", "14 tiles · 25 pts/m²", 10], ["Preprocess", "DSM / DTM / trees 0.5 m", 180], ["Roof planes", "region growing, BAG", 350],
     ["Shadow-aware sun", "horizon scan, Hay–Davies", 520], ["PV & economics", "hourly, 2026 vs 2027", 690], ["Heritage filter", "RCE + BGT, indicative", 860]]
    .map(([t, s, x]) => `<rect class="${x === 520 || x === 690 ? "a" : "b"}" x="${x}" y="70" width="160" height="62" rx="8"/>
      <text class="t" x="${+x + 12}" y="96">${t}</text><text class="s" x="${+x + 12}" y="116">${s}</text>`).join("")}
  ${[170, 340, 510, 680, 850].map((x) => `<path class="l" d="M${x},101 H${x + 10}"/>`).join("")}
  <rect class="b" x="350" y="170" width="160" height="56" rx="8"/><text class="t" x="362" y="194">Validation</text>
  <text class="s" x="362" y="212">3D Basisvoorziening, PVGIS</text><path class="l" d="M430,132 V170"/>
  <rect class="b" x="180" y="170" width="160" height="56" rx="8"/><text class="t" x="192" y="194">Change 2023→26</text>
  <text class="s" x="192" y="212">AHN5 vs AHN6 DSM</text><path class="l" d="M260,132 V170"/>
  <rect class="b" x="690" y="170" width="160" height="56" rx="8"/><text class="t" x="702" y="194">Uncertainty</text>
  <text class="s" x="702" y="212">Monte Carlo, 5 factors</text><path class="l" d="M770,132 V170"/>
  <rect class="b" x="860" y="170" width="160" height="56" rx="8"/><text class="t" x="872" y="194">Web twin</text>
  <text class="s" x="872" y="212">3D Tiles, CityJSON, GeoJSON</text><path class="l" d="M940,132 V170"/>
  <text class="s" x="10" y="40">Inputs: AHN6 · BAG · CBS · PVGIS-SARAH3 TMY · MFFBAS/NEDU E1A profile · CBS tariffs · RCE heritage · BGT</text>
</svg>`;

export function renderScience(el: HTMLElement, about: HTMLElement, site: any) {
  const v = site.validation, c = site.campus;
  const steps = c.zhou_like_steps as any[];
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">Method &amp; validation</div><h2>How the twin is built — and how we know it is right</h2>
      <p class="lede">Buildings are reconstructed from the newest Dutch LiDAR (AHN6, flown ${site.data.flights.join(" and ")}),
      ${num(site.data.points_million)} million laser points over ${site.data.n_tiles} square-kilometre tiles. Every step is checked against an independent source.</p></div>
    <div class="card pipeline">${PIPELINE}</div>

    <h3 style="margin-top:28px">Reconstruction vs Kadaster 3D Basisvoorziening 2025 (roofer on AHN5)</h3>
    <div class="kpis">
      <div class="card"><div class="v">${pct(v.all.match_rate, 1)}</div><div class="l">roof planes ≥ 10 m² matched to a reference roof</div></div>
      <div class="card"><div class="v">${num(v.all.slope_median_abs_deg, 2)}°</div><div class="l">median roof-slope error</div></div>
      <div class="card"><div class="v">${num(100 * v.all.dz_median_m, 1)} cm</div><div class="l">median plane-to-reference offset</div></div>
      <div class="card"><div class="v">${num(100 * v.all.h70_median_abs_m, 1)} cm</div><div class="l">median roof-height error, ${num(v.all.n_buildings_heights)} buildings</div></div>
      <div class="card"><div class="v">${signedPct(v.pvgis.bias_pct_tmy_adjusted / 100, 1)}</div><div class="l">irradiance bias vs PVGIS on unshaded roofs (RMSE ${num(v.pvgis.rmse_pct_tmy_adjusted, 1)} %)</div></div>
    </div>

    <div class="grid2">
      <div class="card"><h3>Sun on unshaded roofs vs PVGIS</h3><div class="chart" id="c-pvgis"></div>
        <p class="muted small">Annual in-plane irradiation per tilt/orientation bin; dot size = number of roof planes. Raw bias
        ${signedPct(v.pvgis.bias_pct_weighted / 100, 1)}, of which ${signedPct(v.pvgis.tmy_vs_longterm_ghi_ratio - 1, 1)} is the typical year being darker than 2005–2023.</p></div>
      <div class="card"><h3>How uncertain are the district totals?</h3><div class="chart" id="c-unc"></div>
        <p class="muted small">Median and 5–95 % of ${num(site.uncertainty_config.n_draws)} Monte Carlo draws: building heights and roof
        tilts (${site.uncertainty_config.n_geometry} re-runs of the shading model), weather year 2005–2023, performance ratio, tree transmissivity and flat-roof layout.</p></div>
    </div>
    <div class="grid2" style="margin-top:16px">
      <div class="card"><h3>What drives the uncertainty (Binnenstad)</h3><div class="chart" id="c-tornado"></div>
        <p class="muted small">5–95 % range of each factor alone, as a multiplier on the estimate. Geometry error is negligible with 25 pts/m² LiDAR.</p></div>
      <div class="card"><h3>Weather year vs the typical year</h3><div class="chart" id="c-years"></div>
        <p class="muted small">Yield of the same roofs under each PVGIS-SARAH3 year, relative to the typical meteorological year used in the model.</p></div>
    </div>
    <div class="grid2" style="margin-top:16px">
      <div class="card"><h3>Trees: small for districts, large for some homes</h3><div class="chart" id="c-trees"></div>
        <p class="muted small">AHN6 was flown leaf-off, so crown transmissivity and crown size were varied. District loss stays ≤ ${pct(Math.max(...site.trees.map((t: any) => t.tree_loss)), 0)}; the share of buildings losing &gt; 10 % changes several-fold.</p></div>
      <div class="card"><h3>TU Delft campus vs Zhou et al. (2022)</h3><div class="chart" id="c-campus"></div>
        <p class="muted small">Our roof-only estimate moved step by step to the published study's assumptions (Solar RRL 6, 2100478: roofs ≈ ${c.zhou.roofs_gwh} GWh/yr).
        The remaining ×${num(steps[steps.length - 1].ratio_to_zhou_roofs, 2)} reflects per-module shading rules, opaque trees, flat-mounted panels on protected buildings and scope.</p></div>
    </div>

    <h3 style="margin-top:28px">Results by study area</h3>
    <div class="table-wrap card"><table>
      <thead><tr><th></th><th>Technical GWh/yr (5–95 %)</th><th>Permitted, with permit</th><th>Permitted, no permit</th>
        <th>Home demand covered</th><th>Used on site → with battery</th><th>Value change 2027 → with battery</th></tr></thead>
      <tbody>${AOIS.map((a) => {
        const r = site.aoi[a], u = r.uncertainty, p = r.pv;
        const q = (k: string) => `${num(u[k][1], 1)} (${num(u[k][0], 1)}–${num(u[k][2], 1)})`;
        return `<tr><td>${AOI_LABEL[a]}</td><td>${q("technical_gwh_5_50_95")}</td><td>${q("permitted_incl_permit_gwh_5_50_95")}</td>
          <td>${q("permitted_no_permit_gwh_5_50_95")}</td><td>${pct(p.residential_coverage)}</td>
          <td>${pct(p.scr_aggregate)} → ${pct(p.scr_aggregate_battery)}</td>
          <td>${signedPct(p.value_change_2027_pct / 100)} → ${signedPct(p.value_2027_battery_meur / p.value_2026_meur - 1)}</td></tr>`;
      }).join("")}</tbody></table></div>`;

  // ---------------- charts
  const bins = v.pvgis_bins as any[];
  const lo = Math.floor((Math.min(...bins.map((b) => Math.min(b.ours, b.pvgis))) - 20) / 50) * 50;
  const hi = Math.ceil((Math.max(...bins.map((b) => Math.max(b.ours, b.pvgis))) + 20) / 50) * 50;
  chart(el.querySelector("#c-pvgis")!, {
    tooltip: { trigger: "item", formatter: (p: any) => `tilt ${p.data[2]}°, azimuth ${p.data[3]}°<br>PVGIS ${p.data[0]} · ours ${p.data[1]} kWh/m²<br>${p.data[4]} planes` },
    xAxis: axis("PVGIS 5.3 (kWh/m²·yr)", { min: lo, max: hi }),
    yAxis: axis("This model (kWh/m²·yr)", { min: lo, max: hi, nameGap: 42 }),
    series: [
      { type: "scatter", data: bins.map((b) => [b.pvgis, b.ours, b.tilt_b, b.asp_b, b.n]),
        symbolSize: (d: number[]) => 5 + Math.sqrt(d[4]) * 0.9, itemStyle: { color: ACC, opacity: 0.8 } },
      { type: "line", data: [[lo, lo], [hi, hi]], symbol: "none", lineStyle: { color: TXT, type: "dashed" }, tooltip: { show: false } },
    ],
  });

  const scen = [["technical", "Technical"], ["permitted_incl_permit", "Permitted (permit)"], ["permitted_no_permit", "No permit"]];
  chart(el.querySelector("#c-unc")!, {
    tooltip: { trigger: "item" },
    xAxis: { type: "category", data: AOIS.map((a) => AOI_LABEL[a]), axisLabel: { color: TXT }, axisLine: { lineStyle: { color: LINE } } },
    yAxis: axis("GWh/yr", { nameGap: 36 }),
    series: scen.map(([k, name], i) => ({
      name, type: "boxplot", itemStyle: { color: ["#13302d", "#3b2f1c", "#3b1f24"][i], borderColor: [ACC, "#f6ad55", "#fc8181"][i] },
      data: AOIS.map((a) => { const q = site.aoi[a].uncertainty[`${k}_gwh_5_50_95`]; return [q[0], q[0], q[1], q[2], q[2]]; }),
      tooltip: { formatter: (p: any) => {
        const q = site.aoi[AOIS[p.dataIndex]].uncertainty[`${k}_gwh_5_50_95`];
        return `${AOI_LABEL[AOIS[p.dataIndex]]} · ${name}<br>median ${num(q[1], 1)} GWh/yr<br>5–95 %: ${num(q[0], 1)}–${num(q[2], 1)}`;
      } },
    })),
  });

  const oat = site.aoi.binnenstad.uncertainty.one_at_a_time_5_95 as Record<string, number[]>;
  const fac = Object.entries(oat).sort((a, b) => (a[1][1] - a[1][0]) - (b[1][1] - b[1][0]));
  chart(el.querySelector("#c-tornado")!, {
    grid: { left: 120, right: 24, top: 16, bottom: 44 },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: (p: any) => `${p[0].name}: ×${num(fac[p[0].dataIndex][1][0], 3)} – ×${num(fac[p[0].dataIndex][1][1], 3)}` },
    xAxis: axis("multiplier on the estimate", { min: 0.8, max: 1.2 }),
    yAxis: { type: "category", data: fac.map(([k]) => k.replace(/_/g, " ")), axisLabel: { color: TXT }, axisLine: { lineStyle: { color: LINE } } },
    series: [
      { type: "bar", stack: "r", data: fac.map(([, r]) => r[0]), itemStyle: { color: "transparent" }, silent: true },
      { type: "bar", stack: "r", data: fac.map(([, r]) => r[1] - r[0]), itemStyle: { color: ACC }, barWidth: 14,
        markLine: { symbol: "none", data: [{ xAxis: 1 }], lineStyle: { color: TXT, type: "dashed" }, label: { show: false } } },
    ],
  });

  const yrs = site.weather_years as any[];
  chart(el.querySelector("#c-years")!, {
    xAxis: { type: "category", data: [...new Set(yrs.map((y) => y.year))], axisLabel: { color: TXT }, axisLine: { lineStyle: { color: LINE } } },
    yAxis: axis("yield / typical year", { min: 0.9, max: 1.2, nameGap: 40 }),
    series: AOIS.map((a) => ({ name: AOI_LABEL[a], type: "line", symbolSize: 5, itemStyle: { color: AOI_COL[a] },
      data: yrs.filter((y) => y.aoi === a).map((y) => +y.factor.toFixed(3)),
      markLine: a === "binnenstad" ? { symbol: "none", data: [{ yAxis: 1 }], lineStyle: { color: TXT, type: "dashed" }, label: { show: false } } : undefined })),
  });

  const order = ["sparse", "base", "dense", "opaque", "crown+1m", "crown+2m"];
  chart(el.querySelector("#c-trees")!, {
    xAxis: { type: "category", data: order, axisLabel: { color: TXT }, axisLine: { lineStyle: { color: LINE } } },
    yAxis: axis("% of buildings losing > 10 %", { nameGap: 36 }),
    series: AOIS.map((a) => ({ name: AOI_LABEL[a], type: "line", symbolSize: 6, itemStyle: { color: AOI_COL[a] },
      data: order.map((o) => +(100 * site.trees.find((t: any) => t.aoi === a && t.scenario === o).share_bldg_tree_loss_gt10pct).toFixed(1)) })),
  });

  chart(el.querySelector("#c-campus")!, {
    grid: { left: 56, right: 18, top: 24, bottom: 92 },
    xAxis: { type: "category", data: steps.map((s) => s.step.replace(/\s*\(.*\)/, "").replace("+ ", "+\n")),
      axisLabel: { color: TXT, interval: 0, fontSize: 10 }, axisLine: { lineStyle: { color: LINE } } },
    yAxis: axis("roof GWh/yr", { nameGap: 36 }),
    series: [{ type: "bar", data: steps.map((s) => +s.roof_gwh_yr.toFixed(2)), itemStyle: { color: ACC }, barWidth: 34,
      label: { show: true, position: "top", color: TXT, formatter: (p: any) => num(p.value, 1) },
      markLine: { symbol: "none", data: [{ yAxis: c.zhou.roofs_gwh, name: "Zhou et al. roofs" }],
        lineStyle: { color: "#f6ad55", type: "dashed" }, label: { color: "#f6ad55", formatter: `Zhou et al. roofs ${c.zhou.roofs_gwh}` } } }],
  });

  // ---------------- limitations, data, credits
  const pr = site.prices;
  about.innerHTML = `
    <div class="grid2">
      <div><h2>Limitations</h2><ul class="clean">
        <li><b>Heritage rules are indicative.</b> Encoded from Delft's protected-cityscape policy as reported in 2019 (no panels visible from public
          space; ≥ ${site.heritage_rules.front_setback_m} m behind the front façade). Current municipal criteria could not be confirmed; municipal monuments are not included.</li>
        <li><b>Leaf-off LiDAR.</b> Both flights were in winter; tree shading is varied in a sensitivity test rather than measured.</li>
        <li><b>Demand</b> is CBS 2024 grid delivery per dwelling (gross use is not published for 2024) shaped by the 2026 E1A profile; non-residential demand is not modelled.</li>
        <li><b>Prices</b> are CBS averages ${pr.months.replace("..", " – ").replace(/MM/g, "-")}: €${num(pr.retail_marginal, 3)}/kWh avoided,
          €${num(pr.export_2027, 3)}/kWh exported from 2027 (50 % of the bare supply tariff). Supplier feed-in costs and installation cost are not included.</li>
        <li><b>Hourly PV</b> uses unobstructed plane-of-array profiles scaled to each plane's shaded annual total.</li>
        <li><b>3D geometry</b> is simplified for the web (roof fragments &lt; 4 m² merged for display; results stay per original plane). CO₂ avoided is not shown: no sourced emission factor.</li>
      </ul></div>
      <div><h2>Data &amp; licences</h2><ul class="clean">
        <li>AHN6 point clouds and DSM/DTM — Het Waterschapshuis / AHN, CC-BY</li>
        <li>BAG building register, BGT large-scale topography — Kadaster via PDOK</li>
        <li>3D Basisvoorziening 2025 (validation) — Kadaster via PDOK</li>
        <li>CBS wijken en buurten 2024 and tariffs (85592NED) — CBS, CC BY 4.0</li>
        <li>Standard load profiles 2026 (E1A) — MFFBAS / NEDU</li>
        <li>PVGIS 5.3 (SARAH-3 TMY and series) — European Commission JRC</li>
        <li>Rijksmonumenten and protected cityscapes — RCE via PDOK</li>
        <li>Aerial photo (3D view) — Beeldmateriaal Nederland via PDOK, CC BY 4.0</li>
        <li>Map basemap — © OpenStreetMap contributors © CARTO</li>
        <li>Zhou et al. (2022) Solar RRL 6, 2100478 — campus benchmark</li>
      </ul>
      <div class="card" style="margin-top:16px"><h3>About</h3>
        <p class="muted">A portfolio research project by Emna (geomatics engineering). Pipeline in Python (laspy, numba, pvlib, geopandas);
        site in Vite, CesiumJS, MapLibre and ECharts. Built with the help of an AI coding assistant.</p></div>
      </div>
    </div>`;
}
