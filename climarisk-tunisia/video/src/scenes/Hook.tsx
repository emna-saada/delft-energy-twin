import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, FONT } from '../theme';
import type { Props } from '../types';
import { Title, TunisiaMap, useAppear } from './common';

export const Hook: React.FC<Props> = ({ svg, kpi }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [40, 330], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const pts = interpolate(frame, [20, 80], [0, 1], { extrapolateRight: 'clamp' });
  const s = useAppear(150);
  return (
    <AbsoluteFill style={{ flexDirection: 'row', alignItems: 'center', padding: '0 120px', gap: 80 }}>
      <div style={{ flex: 1 }}>
        <Title size={76} delay={8}>Quand le climat change,</Title>
        <Title size={76} delay={22} color={C.amber}>le risque de crédit change aussi.</Title>
        <div style={{ marginTop: 40, fontFamily: FONT, fontSize: 30, color: C.mist, opacity: s, maxWidth: 820, lineHeight: 1.4 }}>
          {kpi.n.toLocaleString('fr-FR')} crédits synthétiques · {kpi.ngov} gouvernorats · chaleur, sécheresse, inondation, feux
        </div>
        <div style={{ marginTop: 26, display: 'flex', gap: 16, opacity: s, fontFamily: FONT }}>
          {['Aujourd’hui', 'SSP5-8.5 · 2050'].map((l, i) => (
            <div key={l} style={{ padding: '8px 18px', borderRadius: 99, fontSize: 22, fontWeight: 600,
              background: (i === 0 ? t < 0.5 : t >= 0.5) ? C.amber : 'rgba(255,255,255,0.1)',
              color: (i === 0 ? t < 0.5 : t >= 0.5) ? C.ink : C.mist }}>{l}</div>
          ))}
        </div>
      </div>
      <TunisiaMap svg={svg} t={t} height={900} pointsOpacity={pts} />
    </AbsoluteFill>
  );
};
