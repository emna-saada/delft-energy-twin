import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, FONT, riskColor } from '../theme';
import type { Props } from '../types';
import { Card, Counter, Title, useAppear } from './common';

const SC: Record<string, string> = { baseline: '#7A8B8F', ssp245: C.teal, ssp585: C.red };

export const Results: React.FC<Props> = ({ kpi, periods, heatmap }) => {
  const frame = useCurrentFrame();
  const vmax = Math.max(...periods.map((p) => p.p90)) * 1.1;
  const hm = useAppear(560);
  const H = 330;
  return (
    <AbsoluteFill style={{ padding: '140px 100px 150px 100px', fontFamily: FONT, color: C.white }}>
      <Title size={52} delay={5}>Ce que montre le pipeline</Title>
      <div style={{ display: 'flex', gap: 28, marginTop: 30 }}>
        <Card delay={20} style={{ flex: 1 }}>
          <div style={{ fontSize: 22, color: C.mist, letterSpacing: 2, fontWeight: 600 }}>EAD EN ZONE D’ALÉA ÉLEVÉ</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 20, marginTop: 6 }}>
            <Counter from={0} to={kpi.share0} delay={30} suffix=" %" size={64} color={C.mist} />
            <span style={{ fontSize: 50, color: C.amber }}>→</span>
            <Counter from={kpi.share0} to={kpi.share5} delay={70} dur={70} suffix=" %" size={96} color={C.amber} />
          </div>
          <div style={{ fontSize: 22, color: C.mist }}>aujourd’hui → SSP5-8.5 · 2050 · bande modèles {kpi.share5_p10.toFixed(1).replace('.', ',')}–{kpi.share5_p90.toFixed(1).replace('.', ',')} %</div>
        </Card>
        <Card delay={120} accent={C.red} style={{ flex: 1 }}>
          <div style={{ fontSize: 22, color: C.mist, letterSpacing: 2, fontWeight: 600 }}>EL CLIMATIQUE ADDITIONNELLE · 2050</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginTop: 6 }}>
            <Counter from={0} to={kpi.el5} delay={140} dur={60} suffix=" M TND" size={84} />
          </div>
          <div style={{ fontSize: 22, color: C.mist }}>
            soit <b style={{ color: C.white }}>{kpi.bp5.toFixed(0)} pb</b> de l’EAD · bande {kpi.el5_p10.toFixed(1).replace('.', ',')}–{kpi.el5_p90.toFixed(1).replace('.', ',')} M TND
          </div>
        </Card>
      </div>
      <div style={{ display: 'flex', gap: 28, marginTop: 28, alignItems: 'flex-start' }}>
        <Card delay={260} accent={C.teal} style={{ flex: 1.15 }}>
          <div style={{ fontSize: 22, color: C.mist, fontWeight: 600, letterSpacing: 2 }}>EL ADDITIONNELLE PAR SCÉNARIO (M TND, médiane et 10–90 %)</div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 26, height: H, marginTop: 16, paddingBottom: 6 }}>
            {periods.map((p, i) => {
              const g = interpolate(frame, [290 + i * 25, 330 + i * 25], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              const h = (p.med / vmax) * (H - 70) * g;
              const lo = (p.p10 / vmax) * (H - 70); const hi = (p.p90 / vmax) * (H - 70);
              return (
                <div key={p.key} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 + Math.max(0, hi - h), opacity: g, fontFamily: '"JetBrains Mono"' }}>{p.med.toFixed(1).replace('.', ',')}</div>
                  <div style={{ width: '100%', height: h, background: SC[p.key.split('_')[0]], borderRadius: '8px 8px 0 0', position: 'relative' }}>
                    <div style={{ position: 'absolute', left: '50%', width: 2, background: C.white, opacity: g * 0.8,
                      bottom: lo - h + h, height: hi - lo, transform: 'translateX(-1px)', top: undefined }} />
                  </div>
                  <div style={{ fontSize: 17, color: C.mist, marginTop: 8, textAlign: 'center', height: 44 }}>{p.label}</div>
                </div>
              );
            })}
          </div>
        </Card>
        <Card delay={540} accent={C.amber} style={{ flex: 1 }}>
          <div style={{ fontSize: 22, color: C.mist, fontWeight: 600, letterSpacing: 2 }}>SECTEUR × ALÉA · SSP5-8.5 · 2050</div>
          <div style={{ display: 'grid', gridTemplateColumns: `200px repeat(${heatmap.cols.length}, 1fr)`, gap: 4, marginTop: 14, opacity: hm }}>
            <div />
            {heatmap.cols.map((c) => <div key={c} style={{ fontSize: 17, color: C.mist, textAlign: 'center' }}>{c}</div>)}
            {heatmap.rows.map((r, i) => (
              <React.Fragment key={r}>
                <div style={{ fontSize: 17, color: C.white, whiteSpace: 'nowrap', overflow: 'hidden' }}>{r}</div>
                {heatmap.values[i].map((v, j) => {
                  const a = interpolate(frame, [570 + (i + j) * 6, 590 + (i + j) * 6], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
                  return <div key={j} style={{ background: riskColor(v), opacity: a, borderRadius: 4, height: 26, fontSize: 15,
                    color: v > 0.55 ? C.white : C.ink, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: '"JetBrains Mono"' }}>{v.toFixed(2)}</div>;
                })}
              </React.Fragment>
            ))}
          </div>
        </Card>
      </div>
    </AbsoluteFill>
  );
};
