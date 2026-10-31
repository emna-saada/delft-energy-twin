// Story sections between the 3D twin and the method: context, districts, sun & demand, 2027, heritage, change.
// Every number is read from data/site.json (written by the Python pipeline).
import { AOI_COL, C, axis, catAxis, chart } from "./charts";
import { AOI_LABEL, AOIS, AoiKey, eur, num, pct, signedPct } from "./data";

const ICON = {
  scan: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M3 7V4h3M21 7V4h-3M3 17v3h3M21 17v3h-3"/><circle cx="8" cy="9" r=".8"/><circle cx="12" cy="8" r=".8"/><circle cx="16" cy="10" r=".8"/><circle cx="9" cy="14" r=".8"/><circle cx="14" cy="15" r=".8"/></svg>`,
  euro: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M17 6.5A6.5 6.5 0 1 0 17 17.5M4 10h9M4 14h9"/></svg>`,
  shield: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>`,
};
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function context(el: HTMLElement, site: any) {
  const b = site.aoi.binnenstad, hb = site.heritage_buildings.binnenstad;
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">Why this study</div>
      <h2>Three things are happening in Delft at once</h2>
      <p class="lede">The Netherlands has just flown a new national laser scan, the rules for rooftop solar change on 1 January 2027,
      and Delft's historic centre is protected. This twin puts the three together, roof by roof.</p></div>
    <div class="grid3">
      <div class="card ctx" style="--c:var(--ink)"><div class="icon">${ICON.scan}</div>
        <div class="num">${num(site.data.points_million)}<small>million laser points</small></div>
        <h3>A brand-new laser scan (AHN6)</h3>
        <p class="muted">Aircraft scanned Delft on ${site.data.flights.join(" and ")}: ${num(site.data.building_pts_m2[0])}–${num(site.data.building_pts_m2[1])}
        points on every square metre of roof. From them we rebuild the shape, slope and orientation of every roof, and the
        buildings and trees that shade it.</p></div>
      <div class="card ctx" style="--c:var(--loss)"><div class="icon">${ICON.euro}</div>
        <div class="num">${signedPct(b.pv.value_change_2027_pct / 100)}<small>value of home panels, Binnenstad</small></div>
        <h3>Net metering ends on 1 January 2027</h3>
        <p class="muted">Today, power you export is subtracted from what you buy (the <i>salderingsregeling</i>), worth
        €${num(site.prices.retail_marginal, 2)} per kWh. From 2027 exported power earns at least €${num(site.prices.export_2027, 2)}.
        What matters becomes how much solar power a home <b>uses itself</b>.</p></div>
      <div class="card ctx" style="--c:var(--delft)"><div class="icon">${ICON.shield}</div>
        <div class="num">${num(hb.in_view)}<small>protected buildings</small></div>
        <h3>A protected historic centre</h3>
        <p class="muted">The Binnenstad is a protected cityscape with ${num(hb.monuments)} national monuments. Panels may not be
        visible from the street, so the potential that is <b>allowed</b> is smaller than what is <b>technically</b> possible.</p></div>
    </div>
    <div class="split" style="margin-top:44px">
      <figure><img src="${import.meta.env.BASE_URL}img/shadows.jpg" alt="Canal houses in the 3D twin with morning shadows" loading="lazy" />
        <figcaption>The twin at 09:30 on 21 June: each roof surface is coloured by the sun it receives over a whole year, after shadows from buildings and trees.</figcaption></figure>
      <div><h3>How to read the 3D twin</h3>
        <ol class="steps">
          <li><div><b>Colours = sun on the roof.</b> Yellow roofs get up to 1,200 kWh per m² per year; purple ones are shaded or face north.</div></li>
          <li><div><b>Pick a scenario.</b> “Technical” counts every usable roof; the two “permitted” scenarios apply the heritage rules.</div></li>
          <li><div><b>Move the sun.</b> The date and hour controls cast real shadows — winter sun is low, so narrow streets stay dark.</div></li>
          <li><div><b>Click a building or search an address.</b> You get its roof, its panels, and what they are worth before and after 2027.</div></li>
        </ol>
        <p style="margin-top:18px"><a class="btn" href="#twin">↑ Back to the 3D twin</a></p></div>
    </div>`;
}

function districts(el: HTMLElement, site: any) {
  const tag: Record<AoiKey, string> = {
    binnenstad: "Medieval canal houses, steep roofs, protected cityscape",
    campus: "Large flat-roofed university buildings and student housing",
    voorhof: "Post-war flats and terraced houses, mostly flat roofs",
  };
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">Study areas</div>
      <h2>Three very different neighbourhoods</h2>
      <p class="lede">The same model, three kinds of city. Numbers are a year's solar power from rooftops (median and 5–95 % range
      of the uncertainty analysis), before and after heritage rules.</p></div>
    <div class="grid3">${AOIS.map((a) => {
      const r = site.aoi[a], u = r.uncertainty.technical_gwh_5_50_95, p = r.pv;
      return `<div class="card district" style="--c:${AOI_COL[a]}"><h3>${AOI_LABEL[a]}</h3><div class="tagline">${tag[a]}</div>
        <div class="big">${num(u[1], 1)} <span class="small muted">GWh / year (${num(u[0], 1)}–${num(u[2], 1)})</span></div>
        <div class="chart short" id="d-${a}"></div>
        <div class="stat-row"><span>Buildings with a usable roof</span><span>${num(p.n_with_pv_potential)} of ${num(p.n_buildings)}</span></div>
        <div class="stat-row"><span>Home electricity it could cover</span><span>${pct(p.residential_coverage)}</span></div>
        <div class="stat-row"><span>Roof sun lost to shading</span><span>${pct(r.aoi_summary.loss_all_obstructions)}</span></div>
        <div class="stat-row"><span>Share of roof area that is flat</span><span>${pct(r.aoi_summary.share_flat_area)}</span></div></div>`;
    }).join("")}</div>`;
  for (const a of AOIS) {
    const u = site.aoi[a].uncertainty;
    const vals = ["technical", "permitted_incl_permit", "permitted_no_permit"].map((k) => +u[`${k}_gwh_5_50_95`][1].toFixed(1));
    chart(el.querySelector(`#d-${a}`)!, {
      grid: { left: 92, right: 36, top: 6, bottom: 6 }, tooltip: { show: false },
      xAxis: { type: "value", show: false, max: Math.max(...vals) * 1.15 },
      yAxis: catAxis(["Technical", "With permit", "No permit"], { inverse: true, axisLine: { show: false } }),
      series: [{ type: "bar", data: vals, barWidth: 11,
        itemStyle: { color: (p: any) => [AOI_COL[a], AOI_COL[a] + "B3", AOI_COL[a] + "66"][p.dataIndex] },
        label: { show: true, position: "right", color: C.ink2, formatter: "{c}" } }],
    });
  }
}

function year(el: HTMLElement, site: any) {
  const e = site.energy;
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">Sun and demand</div>
      <h2>Solar comes in summer and at noon. Homes use power in winter and in the evening.</h2>
      <p class="lede">That mismatch is why the end of net metering matters, and why streets with many panels push power back into
      the grid at midday. Production is all rooftop PV on homes in the district; demand is their electricity use.</p></div>
    <div class="chips" id="year-aoi" role="group" aria-label="Study area">${AOIS.map((a, i) => `<button data-a="${a}" aria-pressed="${i === 0}">${AOI_LABEL[a]}</button>`).join("")}</div>
    <div class="grid2" style="margin-top:16px">
      <div class="card"><h3>Month by month</h3><div class="chart" id="c-month"></div></div>
      <div class="card"><h3>An average day in June and December</h3><div class="chart" id="c-day"></div></div>
    </div>
    <div class="callout" id="year-note"></div>`;
  const cm = chart(el.querySelector("#c-month")!, {});
  const cd = chart(el.querySelector("#c-day")!, {});
  const draw = (a: AoiKey) => {
    const m = e[a].monthly_gwh, d = e[a].day_mw;
    cm.setOption({
      legend: { top: 4, left: 0, icon: "rect", itemWidth: 12, itemHeight: 8, textStyle: { color: C.ink2 } },
      xAxis: catAxis(MONTHS), yAxis: axis("GWh", { nameGap: 38 }),
      series: [
        { name: "Solar production", type: "bar", data: m.pv, barWidth: "62%", itemStyle: { color: C.solar } },
        { name: "Home demand", type: "line", data: m.demand, symbol: "circle", symbolSize: 6, lineStyle: { width: 2, color: C.ink }, itemStyle: { color: C.ink } },
      ],
    }, true);
    const hours = [...Array(24).keys()].map((h) => `${h}:00`);
    cd.setOption({
      legend: { top: 4, left: 0, icon: "rect", itemWidth: 12, itemHeight: 8, textStyle: { color: C.ink2 } },
      xAxis: catAxis(hours, { axisLabel: { color: C.ink3, interval: 5 }, boundaryGap: false }), yAxis: axis("MW", { nameGap: 34 }),
      series: [
        { name: "Solar · June", type: "line", data: d.june.pv, smooth: true, symbol: "none", areaStyle: { color: C.solar, opacity: .2 },
          lineStyle: { color: C.solar, width: 2 }, itemStyle: { color: C.solar } },
        { name: "Solar · December", type: "line", data: d.december.pv, smooth: true, symbol: "none", areaStyle: { color: C.winter, opacity: .2 },
          lineStyle: { color: C.winter, width: 2 }, itemStyle: { color: C.winter } },
        { name: "Demand · June", type: "line", data: d.june.demand, smooth: true, symbol: "none",
          lineStyle: { color: C.ink, type: "dashed", width: 1.5 }, itemStyle: { color: C.ink } },
        { name: "Demand · December", type: "line", data: d.december.demand, smooth: true, symbol: "none",
          lineStyle: { color: C.ink, width: 1.5 }, itemStyle: { color: C.ink } },
      ],
    }, true);
    const pk = Math.max(...d.june.pv), dk = d.june.demand[d.june.pv.indexOf(pk)];
    const summer = m.pv.slice(3, 8).reduce((s: number, v: number) => s + v, 0) / m.pv.reduce((s: number, v: number) => s + v, 0);
    el.querySelector("#year-note")!.innerHTML = `<b>${AOI_LABEL[a]}:</b> on an average June day the panels peak at
      <span class="hl">${num(pk, 1)} MW</span> while homes use <b>${num(dk, 1)} MW</b> — the surplus flows into the grid.
      April to August produce <b>${pct(summer)}</b> of the year's solar power; in December it is ${num(m.pv[11], 2)} GWh against ${num(m.demand[11], 2)} GWh of demand.`;
  };
  el.querySelectorAll<HTMLButtonElement>("#year-aoi button").forEach((b) => b.addEventListener("click", () => {
    el.querySelectorAll("#year-aoi button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    draw(b.dataset.a as AoiKey);
  }));
  draw("binnenstad");
}

function value(el: HTMLElement, site: any) {
  const e = site.energy, r = e.prices.retail, x = e.prices.export_2027;
  const regimes = AOIS.map((a) => {
    const k = e[a].residential_kwh;
    return {
      a, y26: [k.netted_kwh * r, k.excess_kwh * x], y27: [k.self_kwh * r, k.export_kwh * x],
      yb: [k.self_batt_kwh * r, k.export_batt_kwh * x],
    };
  });
  const b = site.aoi.binnenstad.pv;
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">What 2027 changes</div>
      <h2>From “export and net it” to “use it yourself”</h2>
      <p class="lede">The same panels, the same sun — but a different price for the power you do not use at home.</p></div>
    <div class="split">
      <div>
        <ol class="steps">
          <li><div><b>Until 31 December 2026 — net metering.</b> Exported kWh are subtracted from the kWh you buy, so almost every
            solar kWh is worth the full price of <b>€${num(r, 3)}</b> (supply + energy tax).</div></li>
          <li><div><b>From 1 January 2027.</b> Only power used at home saves €${num(r, 3)}; exported power earns at least
            <b>€${num(x, 3)}</b> per kWh (50 % of the bare supply price).</div></li>
          <li><div><b>A home battery</b> stores midday surplus for the evening. In the Binnenstad it raises the share used at home from
            ${pct(b.scr_aggregate)} to ${pct(b.scr_aggregate_battery)}.</div></li>
        </ol>
        <div class="callout">Panels on Binnenstad homes lose <b style="color:var(--loss)">${signedPct(b.value_change_2027_pct / 100).replace("−", "")}</b> of their yearly value in 2027,
          or <b style="color:var(--loss)">${signedPct(b.value_2027_battery_meur / b.value_2026_meur - 1).replace("−", "")}</b> with a 5 kWh battery per home.
          Prices: CBS average ${site.prices.months.replace("..", " – ").replace(/MM/g, "-")}.</div>
      </div>
      <div class="card"><h3>Yearly value of rooftop solar on homes (million €)</h3><div class="chart tall" id="c-value"></div>
        <div class="legend-inline"><span><i style="background:${C.home}"></i>used at home (2026: netted)</span><span><i style="background:${C.loss}"></i>exported</span></div></div>
    </div>`;
  const cats: string[] = [], used: number[] = [], exp: number[] = [];
  for (const g of regimes) for (const [lab, v] of [["2026", g.y26], ["2027", g.y27], ["+batt", g.yb]] as [string, number[]][]) {
    cats.push(lab); used.push(+(v[0] / 1e6).toFixed(3)); exp.push(+(v[1] / 1e6).toFixed(3));
  }
  chart(el.querySelector("#c-value")!, {
    grid: { left: 52, right: 12, top: 18, bottom: 58 }, legend: { show: false },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v: number) => eur(v * 1e6),
      formatter: undefined },
    // two-row axis: regime under each bar, study area under each group of three
    xAxis: [catAxis(cats, { axisLabel: { color: C.ink3, interval: 0, fontSize: 10 } }),
      catAxis(AOIS.map((a) => AOI_LABEL[a]), { position: "bottom", offset: 22, axisLine: { show: false },
        axisLabel: { color: C.ink, fontWeight: 600, fontSize: 11 }, axisPointer: { show: false } })],
    yAxis: axis("M€ / year", { nameGap: 36 }),
    series: [
      { name: "used at home / netted", type: "bar", stack: "v", data: used, barWidth: "58%", itemStyle: { color: C.home } },
      { name: "exported", type: "bar", stack: "v", data: exp, itemStyle: { color: C.loss } },
    ],
  });
}

function heritage(el: HTMLElement, site: any) {
  const h = site.aoi.binnenstad.heritage, c = site.heritage_cells.binnenstad, rules = site.heritage_rules;
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">Heritage</div>
      <h2>Beautiful roofs, strict rules</h2>
      <p class="lede">Since 2012 Delft allows panels in its protected cityscape only where they cannot be seen from the street.
      We encoded that as an <b>indicative</b> filter on every usable roof cell.</p></div>
    <div class="split">
      <figure><img src="${import.meta.env.BASE_URL}img/heritage-markt.png" alt="Heritage filter around the Markt" loading="lazy" />
        <figcaption>Around the Markt: <b style="color:var(--ok)">green</b> allowed, <b style="color:var(--permit)">orange</b> needs a permit
        (national monument), <b style="color:var(--loss)">red</b> not allowed; teal lines are façades that face the street.</figcaption></figure>
      <div>
        <ol class="steps">
          <li><div><b>Find the street side.</b> From every metre of façade we look outward; if the view reaches a road, square or canal
            within ${rules.front_ray_m} m before another building, it is a front façade.</div></li>
          <li><div><b>Keep panels out of sight.</b> No panels within ${rules.front_setback_m} m of a front façade, and none on roof faces
            that slope down towards the street.</div></li>
          <li><div><b>Monuments need a permit.</b> National monuments (rijksmonumenten) are possible only with an individual permit.</div></li>
        </ol>
        <div class="kpis" style="margin-top:22px;grid-template-columns:repeat(3,1fr)">
          <div class="card"><div class="v">${num(h.technical.gwh_yr, 1)}</div><div class="l">GWh/yr technical (Binnenstad)</div></div>
          <div class="card"><div class="v" style="color:var(--permit)">${num(h.permitted_incl_permit.gwh_yr, 1)}</div><div class="l">allowed, monuments with permit (${pct(h.permitted_incl_permit.share_of_technical)})</div></div>
          <div class="card"><div class="v" style="color:var(--loss)">${num(h.permitted_no_permit.gwh_yr, 1)}</div><div class="l">allowed without any permit (${pct(h.permitted_no_permit.share_of_technical)})</div></div>
        </div>
        <p class="note">Of the usable roof surface in the Binnenstad, ${pct(c.permitted)} is allowed, ${pct(c.permit_required)} needs a permit and
          ${pct(c.not_permitted)} is not allowed. The rules come from a 2019 description of Delft's policy and must be checked with the municipality.</p>
      </div>
    </div>`;
}

function change(el: HTMLElement, site: any) {
  const ch = site.change;
  el.innerHTML = `
    <div class="section-head"><div class="eyebrow">A changing city</div>
      <h2>Two laser scans, three years apart</h2>
      <p class="lede">Comparing the 2023 scan (AHN5) with the 2025/26 scan (AHN6) shows what was built, raised, demolished —
      and where solar panels appeared. On unchanged roofs the two scans agree within ${num(100 * ch.noise_unchanged_buildings.nmad_m, 1)} cm.</p></div>
    <div class="kpis">
      <div class="card"><div class="v" style="color:var(--ok)">${num(ch.validation_new.n_detected_new)}</div><div class="l">new buildings (${pct(ch.validation_new.detected_new_with_bouwjaar_ge_2023)} confirmed by their registered year)</div></div>
      <div class="card"><div class="v" style="color:var(--permit)">${num(ch.building_change_counts.raised_or_extended)}</div><div class="l">buildings raised or extended</div></div>
      <div class="card"><div class="v" style="color:var(--loss)">${num(ch.demolitions.n_confirmed_demolished)}</div><div class="l">demolitions confirmed (${num(ch.demolitions.area_confirmed_m2)} m²)</div></div>
      <div class="card"><div class="v" style="color:var(--solar-ink)">${num(ch.pv_flat_roofs.installed_2023_2026.n)}</div><div class="l">solar arrays added on flat roofs since 2023 (${num(ch.pv_flat_roofs.installed_2023_2026.area_m2)} m²)</div></div>
    </div>
    <div class="grid2">
      <div class="card"><h3>Changed buildings per district</h3><div class="chart" id="c-change"></div></div>
      <div class="card"><h3>Solar arrays on flat roofs</h3><div class="chart" id="c-pvnew"></div>
        <p class="note">Arrays are tilted planes 0.15–1.5 m above a flat roof; “added” means the roof was lower in the 2023 scan.</p></div>
    </div>`;
  const kinds: [string, string, string][] = [["new_since_2023", "new", C.ok], ["raised_or_extended", "raised / extended", C.permit], ["lowered", "lowered", C.loss]];
  chart(el.querySelector("#c-change")!, {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: catAxis(AOIS.map((a) => AOI_LABEL[a])), yAxis: axis("buildings", { nameGap: 36 }),
    series: kinds.map(([k, name, col]) => ({ name, type: "bar", barGap: "12%", itemStyle: { color: col },
      data: AOIS.map((a) => site.aoi[a].change?.[k] ?? 0) })),
  });
  const pv = ch.pv_flat_roofs;
  chart(el.querySelector("#c-pvnew")!, {
    tooltip: { trigger: "item", formatter: "{b}: {c} m² ({d} %)" }, legend: { show: false },
    series: [{ type: "pie", radius: ["50%", "74%"], itemStyle: { borderColor: C.surface, borderWidth: 2 },
      label: { color: C.ink2, formatter: "{b}\n{c} m²" }, labelLine: { lineStyle: { color: C.ink3 } },
      data: [
        { name: "already there in 2023", value: Math.round(pv.present_2023.area_m2), itemStyle: { color: C.neutral } },
        { name: "added 2023–2026", value: Math.round(pv.installed_2023_2026.area_m2), itemStyle: { color: C.solar } },
        { name: "unclear", value: Math.round(pv.unclear.area_m2), itemStyle: { color: "#E9E5DC" } },
      ] }],
  });
}

export function renderStory(site: any) {
  const $ = (id: string) => document.getElementById(id)!;
  context($("context"), site);
  districts($("districts"), site);
  year($("year"), site);
  value($("value"), site);
  heritage($("heritage"), site);
  change($("change"), site);
}
