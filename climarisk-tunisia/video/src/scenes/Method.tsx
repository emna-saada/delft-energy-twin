import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, FONT, MONO } from '../theme';
import type { Props } from '../types';
import { Card, Title, useAppear } from './common';

const SOURCES = ['NASA NEX-GDDP-CMIP6', 'WRI Aqueduct Floods', 'ESA WorldCover', 'WorldPop', 'geoBoundaries', 'OS-Climate physrisk'];
const BLOCKS = [
  { t: 'Aléa', d: 'chaleur · sécheresse · inondation · feux', c: '#D1495B' },
  { t: 'Exposition', d: 'localisation et EAD de chaque crédit', c: C.teal },
  { t: 'Vulnérabilité', d: 'sensibilité du secteur à chaque aléa', c: '#B7791F' },
];

export const Method: React.FC<Props> = () => {
  const frame = useCurrentFrame();
  const badge = useAppear(560);
  return (
    <AbsoluteFill style={{ padding: '150px 110px', fontFamily: FONT }}>
      <Title size={58} delay={5}>Données ouvertes, méthode explicite</Title>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, marginTop: 36 }}>
        {SOURCES.map((s, i) => {
          const a = interpolate(frame, [20 + i * 12, 40 + i * 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          return <div key={s} style={{ padding: '10px 20px', borderRadius: 99, border: '1px solid rgba(255,255,255,0.25)',
            color: C.white, fontSize: 24, opacity: a, transform: `translateY(${(1 - a) * 20}px)` }}>{s}</div>;
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 22, marginTop: 56 }}>
        {BLOCKS.map((b, i) => (
          <React.Fragment key={b.t}>
            <Card delay={150 + i * 40} accent={b.c} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 42, fontWeight: 800 }}>{b.t}</div>
              <div style={{ fontSize: 22, color: C.mist, marginTop: 8 }}>{b.d}</div>
            </Card>
            <div style={{ fontSize: 56, color: C.amber, fontWeight: 800, opacity: interpolate(frame, [200 + i * 40, 230 + i * 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>
              {i < 2 ? '×' : '→'}
            </div>
          </React.Fragment>
        ))}
        <Card delay={300} accent={C.red} style={{ flex: 1.6 }}>
          <div style={{ fontFamily: MONO, fontSize: 24, lineHeight: 1.7, whiteSpace: 'nowrap' }}>
            PD′ = PD · (1 + β·Score)<br />EL = PD′ · LGD′ · EAD
          </div>
        </Card>
      </div>
      <div style={{ marginTop: 46, display: 'flex', justifyContent: 'center', opacity: badge, transform: `scale(${0.9 + 0.1 * badge})` }}>
        <div style={{ padding: '16px 34px', borderRadius: 16, background: C.amber, color: C.ink, fontSize: 32, fontWeight: 800 }}>
          Portefeuille 100 % synthétique — aucune donnée personnelle
        </div>
      </div>
    </AbsoluteFill>
  );
};
