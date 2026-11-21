/* ClimaRisk Tunisie results site: loads data/*.json (written by scripts/build_site.py) and draws the figures. */
(function () {
  'use strict';
  const COL = { Today: '#9a9a9a', 'SSP2-4.5': '#1f5f99', 'SSP5-8.5': '#b23a2e' };
  const RAMP = d3.interpolateRgb('#f7efec', '#7e1f17');
  const PNAME = { baseline: 'current climate', ssp245_2030: 'SSP2-4.5, 2030', ssp245_2050: 'SSP2-4.5, 2050', ssp585_2030: 'SSP5-8.5, 2030', ssp585_2050: 'SSP5-8.5, 2050' };
  const f1 = d3.format(',.1f'), f2 = d3.format(',.2f'), f0 = d3.format(',.0f');
  const tip = document.getElementById('tip');
  let D = null;
  let period = document.getElementById('period').value;

  const files = ['scenarios', 'portfolio', 'sectors', 'governorates', 'heatmap', 'sensitivity', 'top_exposures', 'physrisk', 'tunisia_adm1.geojson'];
  Promise.all(files.map((f) => fetch('data/' + f + '.json').then((r) => { if (!r.ok) throw new Error(f); return r.json(); })))
    .then((res) => {
      D = {};
      files.forEach((f, i) => { D[f.replace('.geojson', '')] = res[i].rows || res[i]; });
      drawAll();
      let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(drawAll, 150); });
    })
    .catch((e) => { document.getElementById('lede').textContent = 'The results could not be loaded (' + e.message + '). Open this page through a web server or GitHub Pages rather than from the file system.'; });

  document.getElementById('period').addEventListener('change', (e) => { period = e.target.value; drawAll(); });

  function showTip(ev, lines) {
    tip.replaceChildren(...lines.map(([b, t]) => { const d = document.createElement('div'); if (b) { const s = document.createElement('b'); s.textContent = b; d.append(s, t ? ' ' + t : ''); } else d.textContent = t; return d; }));
    tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let x = ev.pageX + 14, y = ev.pageY + 14;
    if (x + w > window.scrollX + document.documentElement.clientWidth - 8) x = ev.pageX - w - 14;
    if (y + h > window.scrollY + window.innerHeight - 8) y = ev.pageY - h - 14;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  function hideTip() { tip.hidden = true; }
  const sc = () => D.scenarios;
  const cur = () => sc().find((r) => r.period === period);

  function drawAll() {
    document.querySelectorAll('.period-name').forEach((el) => { el.textContent = PNAME[period]; });
    lede(); summaryTable(); figEL(); figShare(); figMap(); govTable(); figHeat(); figSectors(); figDrivers(); figSens(); prTable(); topTable();
  }

  function lede() {
    const b = sc().find((r) => r.period === 'baseline'), s = sc().find((r) => r.period === 'ssp585_2050');
    const p = D.portfolio[0];
    document.getElementById('lede').textContent =
      'Under SSP5-8.5, the share of the synthetic loan book (' + f0(p.n_loans) + ' loans, ' + f2(p.total_ead_bn).replace(/\.?0+$/, '') + ' bn TND) located in a high-hazard zone rises from ' +
      f1(b.share_high_med) + ' % under the current climate to ' + f1(s.share_high_med) + ' % by 2050. Climate-adjusted extra expected loss reaches ' + f1(s.el_add_m_med) +
      ' M TND (' + f1(s.el_add_bp_med) + ' bp of exposure), ' + f1(s.el_vs_today_m_med) + ' M TND more than under the current climate. Heat drives most of the change; drought then separates rain-fed agriculture from the rest of the book.';
  }

  function summaryTable() {
    const tb = document.querySelector('#summary-table tbody');
    tb.replaceChildren(...sc().map((r) => {
      const tr = document.createElement('tr'); if (r.period === period) tr.className = 'sel';
      const cells = [PNAME[r.period].replace(/^./, (c) => c.toUpperCase()),
        f1(r.share_high_med) + (r.period === 'baseline' ? '' : ' [' + f1(r.share_high_p10) + '–' + f1(r.share_high_p90) + ']'),
        f1(r.el_add_m_med) + ' [' + f1(r.el_add_m_p10) + '–' + f1(r.el_add_m_p90) + ']',
        f1(r.el_add_bp_med),
        r.period === 'baseline' ? '—' : (r.el_vs_today_m_med > 0 ? '+' : '') + f1(r.el_vs_today_m_med)];
      cells.forEach((c, i) => { const td = document.createElement('td'); td.textContent = c; if (i) td.className = 'num'; tr.appendChild(td); });
      return tr;
    }));
  }

  function axisLabelsWrap(sel) {
    sel.selectAll('text').each(function () {
      const t = d3.select(this), parts = t.text().split(', ');
      if (parts.length > 1) { t.text(null); parts.forEach((s, i) => t.append('tspan').attr('x', 0).attr('dy', i ? '1.2em' : '0.9em').text(s)); }
    });
  }
  const shortLabel = (r) => (r.period === 'baseline' ? 'Current' : r.scenario + ', ' + r.horizon);

  function figEL() {
    const el = document.getElementById('fig-el'); el.replaceChildren();
    const rows = sc(), W = el.clientWidth, H = 290, m = { t: 22, r: 6, b: 44, l: 38 };
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const x = d3.scaleBand().domain(rows.map((r) => r.period)).range([m.l, W - m.r]).padding(0.38);
    const y = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.el_add_m_p90) * 1.1]).nice().range([H - m.b, m.t]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(''));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5)).call((g) => g.select('.domain').remove());
    svg.append('text').attr('class', 'vlab dim').attr('x', m.l).attr('y', 10).text('M TND');
    const xa = svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickSizeOuter(0).tickFormat((p) => shortLabel(rows.find((r) => r.period === p))));
    axisLabelsWrap(xa);
    rows.forEach((r) => {
      const bx = x(r.period), bw = x.bandwidth(), c = COL[r.scenario], sel = r.period === period, cx = bx + bw / 2;
      svg.append('rect').attr('x', bx).attr('width', bw).attr('y', y(r.el_add_m_med)).attr('height', y(0) - y(r.el_add_m_med)).attr('fill', c).attr('fill-opacity', sel ? 1 : 0.55);
      svg.append('line').attr('x1', cx).attr('x2', cx).attr('y1', y(r.el_add_m_p10)).attr('y2', y(r.el_add_m_p90)).attr('stroke', '#1a1a1a');
      [r.el_add_m_p10, r.el_add_m_p90].forEach((v) => svg.append('line').attr('x1', cx - 4).attr('x2', cx + 4).attr('y1', y(v)).attr('y2', y(v)).attr('stroke', '#1a1a1a'));
      svg.append('text').attr('class', 'vlab' + (sel ? '' : ' dim')).attr('x', cx).attr('y', y(r.el_add_m_p90) - 5).attr('text-anchor', 'middle').attr('font-weight', sel ? 700 : 400).text(f1(r.el_add_m_med));
      svg.append('rect').attr('x', bx - 8).attr('width', bw + 16).attr('y', m.t).attr('height', H - m.t - m.b).attr('fill', 'transparent')
        .on('pointermove', (ev) => showTip(ev, [[PNAME[r.period], ''], ['Median', f2(r.el_add_m_med) + ' M TND'], ['Model range', f2(r.el_add_m_p10) + '–' + f2(r.el_add_m_p90)], ['Per exposure', f1(r.el_add_bp_med) + ' bp']]))
        .on('pointerleave', hideTip);
    });
  }

  function figShare() {
    const el = document.getElementById('fig-share'); el.replaceChildren();
    const rows = sc(), W = el.clientWidth, H = 290, m = { t: 8, r: 50, b: 30, l: 108 };
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const y = d3.scaleBand().domain(rows.map((r) => r.period)).range([m.t, H - m.b]).padding(0.45);
    const x = d3.scaleLinear().domain([0, 50]).range([m.l, W - m.r]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickSize(-(H - m.t - m.b)).tickFormat(''));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(5).tickFormat((d) => d + ' %')).call((g) => g.select('.domain').remove());
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(8).tickFormat((p) => PNAME[p].replace(/^./, (c) => c.toUpperCase()))).call((g) => g.select('.domain').remove());
    rows.forEach((r) => {
      const cy = y(r.period) + y.bandwidth() / 2, c = COL[r.scenario], sel = r.period === period;
      svg.append('line').attr('x1', x(r.share_high_p10)).attr('x2', x(r.share_high_p90)).attr('y1', cy).attr('y2', cy).attr('stroke', c).attr('stroke-width', 2.5).attr('stroke-opacity', sel ? 1 : 0.55);
      svg.append('circle').attr('cx', x(r.share_high_med)).attr('cy', cy).attr('r', sel ? 6 : 4.5).attr('fill', c).attr('stroke', '#fff').attr('stroke-width', 1.5);
      svg.append('text').attr('class', 'vlab' + (sel ? '' : ' dim')).attr('x', x(Math.max(r.share_high_p90, r.share_high_med)) + 7).attr('y', cy).attr('dy', '0.35em').attr('font-weight', sel ? 700 : 400).text(f1(r.share_high_med) + ' %');
      svg.append('rect').attr('x', m.l).attr('width', W - m.l - m.r).attr('y', y(r.period) - 6).attr('height', y.bandwidth() + 12).attr('fill', 'transparent')
        .on('pointermove', (ev) => showTip(ev, [[PNAME[r.period], ''], ['Median', f1(r.share_high_med) + ' %'], ['Model range', f1(r.share_high_p10) + '–' + f1(r.share_high_p90) + ' %']]))
        .on('pointerleave', hideTip);
    });
  }

  function figMap() {
    const el = document.getElementById('fig-map'); el.replaceChildren();
    const fc = D.tunisia_adm1, rows = D.governorates.filter((r) => r.period === period), by = new Map(rows.map((r) => [r.governorate, r]));
    const max = d3.max(D.governorates, (r) => r.el_add_bp);
    const W = el.clientWidth, H = Math.min(560, Math.max(420, W * 1.05));
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const proj = d3.geoMercator().fitExtent([[4, 4], [W - 4, H - 46]], fc), path = d3.geoPath(proj);
    svg.append('g').selectAll('path').data(fc.features).join('path').attr('d', path)
      .attr('fill', (f) => { const r = by.get(f.properties.governorate); return r ? RAMP(r.el_add_bp / max) : '#eee'; })
      .attr('stroke', '#fff').attr('stroke-width', 0.8)
      .on('pointermove', function (ev, f) { d3.select(this).attr('stroke', '#1a1a1a').raise(); const r = by.get(f.properties.governorate); showTip(ev, [[f.properties.governorate, ''], ['Extra EL', r ? f1(r.el_add_bp) + ' bp' : 'n/a'], ['Model range', r ? f1(r.el_add_bp_p10) + '–' + f1(r.el_add_bp_p90) + ' bp' : ''], ['High-hazard share', r ? f1(r.share_high) + ' %' : '']]); })
      .on('pointerleave', function () { d3.select(this).attr('stroke', '#fff'); hideTip(); });
    const lw = Math.min(220, W - 20), lg = svg.append('g').attr('transform', `translate(6,${H - 34})`);
    const id = 'g' + Math.random().toString(36).slice(2, 7), gr = svg.append('defs').append('linearGradient').attr('id', id);
    d3.range(0, 1.001, 0.25).forEach((t) => gr.append('stop').attr('offset', t).attr('stop-color', RAMP(t)));
    lg.append('rect').attr('width', lw).attr('height', 9).attr('fill', `url(#${id})`).attr('stroke', '#bbb').attr('stroke-width', 0.5);
    const lx = d3.scaleLinear().domain([0, max]).range([0, lw]);
    lg.append('g').attr('class', 'axis').attr('transform', 'translate(0,9)').call(d3.axisBottom(lx).ticks(4).tickSize(4)).call((g) => g.select('.domain').remove());
    lg.append('text').attr('class', 'vlab dim').attr('x', lw + 6).attr('y', 9).text('bp');
  }

  function govTable() {
    const rows = D.governorates.filter((r) => r.period === period).sort((a, b) => b.el_add_bp - a.el_add_bp).slice(0, 12);
    document.querySelector('#gov-table tbody').replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr');
      [r.governorate, f1(r.el_add_bp), f1(r.el_add_bp_p10) + '–' + f1(r.el_add_bp_p90), f1(r.share_high)].forEach((c, i) => { const td = document.createElement('td'); td.textContent = c; if (i) td.className = 'num' + (i === 2 ? ' bp-range' : ''); tr.appendChild(td); });
      return tr;
    }));
  }

  function figHeat() {
    const el = document.getElementById('fig-heat'); el.replaceChildren();
    const hz = ['heat', 'drought', 'flood', 'fire'], hl = { heat: 'Heat', drought: 'Drought', flood: 'Flood', fire: 'Wildfire' };
    const sub = D.heatmap.filter((r) => r.period === period);
    const sectors = Array.from(new Set(sub.map((r) => r.sector))).sort((a, b) => d3.sum(sub.filter((r) => r.sector === b), (r) => r.score) - d3.sum(sub.filter((r) => r.sector === a), (r) => r.score));
    const W = el.clientWidth, lab = Math.min(165, W * 0.36), rh = 30, H = 26 + rh * sectors.length, cw = (W - lab) / hz.length;
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    hz.forEach((h, j) => svg.append('text').attr('class', 'rlab').attr('x', lab + j * cw + cw / 2).attr('y', 14).attr('text-anchor', 'middle').attr('font-weight', 700).text(hl[h]));
    sectors.forEach((s, i) => {
      const yy = 24 + i * rh;
      svg.append('text').attr('class', 'rlab').attr('x', lab - 8).attr('y', yy + rh / 2).attr('dy', '0.35em').attr('text-anchor', 'end').text(s);
      hz.forEach((h, j) => {
        const r = sub.find((q) => q.sector === s && q.hazard === h), v = r ? r.score : 0, fill = RAMP(Math.min(1, v / 0.8));
        svg.append('rect').attr('x', lab + j * cw).attr('y', yy).attr('width', cw - 1).attr('height', rh - 1).attr('fill', fill)
          .on('pointermove', (ev) => showTip(ev, [[s, ''], [hl[h], f2(v)]])).on('pointerleave', hideTip);
        const c = d3.rgb(fill), lum = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255;
        svg.append('text').attr('x', lab + j * cw + cw / 2).attr('y', yy + rh / 2).attr('dy', '0.35em').attr('text-anchor', 'middle').attr('font-size', 11.5).attr('fill', lum > 0.55 ? '#1a1a1a' : '#fff').attr('pointer-events', 'none').text(d3.format('.2f')(v));
      });
    });
  }

  function figSectors() {
    const el = document.getElementById('fig-sectors'); el.replaceChildren();
    const sub = D.sectors.filter((r) => r.period === period).sort((a, b) => b.el_add_bp - a.el_add_bp);
    const W = el.clientWidth, rh = 27, m = { t: 4, r: 44, b: 26, l: Math.min(165, W * 0.36) }, H = m.t + rh * sub.length + m.b;
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const x = d3.scaleLinear().domain([0, d3.max(D.sectors, (r) => r.el_add_bp)]).nice().range([m.l, W - m.r]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(4).tickSize(-(H - m.t - m.b)).tickFormat(''));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(4)).call((g) => g.select('.domain').remove());
    const c = COL[cur().scenario];
    sub.forEach((r, i) => {
      const yy = m.t + i * rh;
      svg.append('text').attr('class', 'rlab').attr('x', m.l - 8).attr('y', yy + rh / 2).attr('dy', '0.35em').attr('text-anchor', 'end').text(r.sector);
      svg.append('rect').attr('x', m.l).attr('y', yy + 6).attr('height', rh - 12).attr('width', Math.max(1, x(r.el_add_bp) - m.l)).attr('fill', c);
      svg.append('text').attr('class', 'vlab').attr('x', x(r.el_add_bp) + 5).attr('y', yy + rh / 2).attr('dy', '0.35em').text(f1(r.el_add_bp));
      svg.append('rect').attr('x', 0).attr('width', W).attr('y', yy).attr('height', rh).attr('fill', 'transparent')
        .on('pointermove', (ev) => showTip(ev, [[r.sector, ''], ['Extra EL', f1(r.el_add_bp) + ' bp, ' + f2(r.el_add_m) + ' M TND'], ['High-hazard share', f1(r.share_high) + ' %']])).on('pointerleave', hideTip);
    });
  }

  function figDrivers() {
    const el = document.getElementById('fig-drivers'); el.replaceChildren();
    const rows = sc(), mets = [
      { k: 'hot35_days', t: 'Days above 35 °C per year', f: (v) => f0(v) },
      { k: 'cdd_days', t: 'Longest dry spell (days)', f: (v) => f0(v) },
      { k: 'prchange_pct', t: 'Change in annual rainfall', f: (v) => (Math.abs(v) < 0.05 ? 'ref.' : (v > 0 ? '+' : '') + f0(v) + ' %') }];
    const W = el.clientWidth, narrow = W < 640, pw = narrow ? W : (W - 40) / 3, ph = 210, H = narrow ? ph * 3 + 20 : ph;
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    mets.forEach((mt, i) => {
      const ox = narrow ? 0 : i * (pw + 20), oy = narrow ? i * (ph + 10) : 0, m = { t: 26, b: 40, l: 4, r: 4 };
      const g = svg.append('g').attr('transform', `translate(${ox},${oy})`);
      g.append('text').attr('class', 'rlab').attr('font-weight', 700).attr('y', 14).text(mt.t);
      const vals = rows.map((r) => r[mt.k]), lo = Math.min(0, d3.min(vals)), hi = Math.max(0, d3.max(vals));
      const x = d3.scaleBand().domain(rows.map((r) => r.period)).range([m.l, pw - m.r]).padding(0.3);
      const y = d3.scaleLinear().domain([lo, hi]).nice().range([ph - m.b, m.t + 16]);
      g.append('line').attr('x1', m.l).attr('x2', pw - m.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', '#767676');
      rows.forEach((r) => {
        const v = r[mt.k], sel = r.period === period, bx = x(r.period), bw = x.bandwidth();
        if (Math.abs(v) >= 0.05) g.append('rect').attr('x', bx).attr('width', bw).attr('y', Math.min(y(0), y(v))).attr('height', Math.abs(y(v) - y(0))).attr('fill', COL[r.scenario]).attr('fill-opacity', sel ? 1 : 0.55);
        g.append('text').attr('class', 'vlab' + (sel ? '' : ' dim')).attr('x', bx + bw / 2).attr('y', v >= 0 ? Math.min(y(0), y(v)) - 4 : y(v) + 12).attr('text-anchor', 'middle').attr('font-weight', sel ? 700 : 400).text(mt.f(v));
        const t = g.append('text').attr('class', 'vlab dim').attr('text-anchor', 'middle').attr('y', ph - m.b + 16);
        (r.period === 'baseline' ? ['Current'] : [r.scenario, r.horizon]).forEach((s, k) => t.append('tspan').attr('x', bx + bw / 2).attr('dy', k ? '1.2em' : 0).text(s));
        g.append('rect').attr('x', bx).attr('width', bw).attr('y', m.t).attr('height', ph - m.t - m.b).attr('fill', 'transparent')
          .on('pointermove', (ev) => showTip(ev, [[PNAME[r.period], ''], [mt.t, mt.f(v)]])).on('pointerleave', hideTip);
      });
    });
  }

  function figSens() {
    const el = document.getElementById('fig-sens'); el.replaceChildren();
    const rows = D.sensitivity.filter((r) => r.test !== 'β × 1.0');
    const W = el.clientWidth, rh = 24, m = { t: 4, r: 50, b: 26, l: Math.min(150, W * 0.36) }, H = m.t + rh * rows.length + m.b;
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
    const x = d3.scaleLinear().domain([-90, 120]).range([m.l, W - m.r]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([-50, 0, 50, 100]).tickSize(-(H - m.t - m.b)).tickFormat(''));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([-50, 0, 50, 100]).tickFormat((d) => (d > 0 ? '+' : '') + d + ' %')).call((g) => g.select('.domain').remove());
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', m.t).attr('y2', H - m.b).attr('stroke', '#1a1a1a');
    rows.forEach((r, i) => {
      const yy = m.t + i * rh, v = r.delta_pct, x0 = x(Math.min(0, v)), w = Math.max(1, Math.abs(x(v) - x(0)));
      svg.append('text').attr('class', 'rlab').attr('x', m.l - 8).attr('y', yy + rh / 2).attr('dy', '0.35em').attr('text-anchor', 'end').text(r.test);
      svg.append('rect').attr('x', x0).attr('y', yy + 6).attr('width', w).attr('height', rh - 12).attr('fill', v >= 0 ? COL['SSP5-8.5'] : COL['SSP2-4.5']);
      svg.append('text').attr('class', 'vlab dim').attr('x', v >= 0 ? x0 + w + 4 : x0 - 4).attr('y', yy + rh / 2).attr('dy', '0.35em').attr('text-anchor', v >= 0 ? 'start' : 'end').text((v > 0 ? '+' : '') + f1(v) + ' %');
    });
  }

  function prTable() {
    document.querySelector('#pr-table tbody').replaceChildren(...D.physrisk.map((r) => {
      const tr = document.createElement('tr');
      [r.indicator, (r.value > 0 ? '+' : '') + f2(r.value)].forEach((c, i) => { const td = document.createElement('td'); td.textContent = c; if (i) td.className = 'num'; tr.appendChild(td); });
      return tr;
    }));
  }

  let sortKey = 'el_add_k', sortDir = -1;
  function topTable() {
    const rows = D.top_exposures.slice().sort((a, b) => (a[sortKey] < b[sortKey] ? -1 : a[sortKey] > b[sortKey] ? 1 : 0) * sortDir);
    document.querySelector('#top-table tbody').replaceChildren(...rows.map((r) => {
      const tr = document.createElement('tr');
      [r.loan, r.sector, r.governorate, f2(r.ead_m), f2(r.score), f1(r.el_add_k)].forEach((c, i) => { const td = document.createElement('td'); td.textContent = c; if (i > 2) td.className = 'num'; tr.appendChild(td); });
      return tr;
    }));
    document.querySelectorAll('#top-table th').forEach((th) => th.setAttribute('aria-sort', th.dataset.key === sortKey ? (sortDir > 0 ? 'ascending' : 'descending') : 'none'));
  }
  document.querySelectorAll('#top-table th').forEach((th) => {
    th.tabIndex = 0;
    const go = () => { const k = th.dataset.key; if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = typeof D.top_exposures[0][k] === 'number' ? -1 : 1; } topTable(); };
    th.addEventListener('click', go); th.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
  });
})();
