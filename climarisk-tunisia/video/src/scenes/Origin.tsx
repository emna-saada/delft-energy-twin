import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, FONT } from '../theme';
import type { Props } from '../types';
import { Card, Title, useAppear } from './common';

const EVENTS = [
  { k: 'Inondations', y: 'Nabeul · septembre 2018', c: '#2B6CB0', d: 'Crues éclair sur le Cap Bon : habitations, routes et cultures touchées.' },
  { k: 'Sécheresse', y: 'Céréaliculture', c: '#B7791F', d: 'Des campagnes céréalières pénalisées par le manque de pluie.' },
  { k: 'Chaleur', y: 'Records de température', c: '#D1495B', d: 'Des étés plus longs et plus chauds, du sud vers le nord.' },
];

export const Origin: React.FC<Props> = () => {
  const s = useAppear(330);
  return (
    <AbsoluteFill style={{ padding: '150px 120px 160px 120px', fontFamily: FONT }}>
      <Title size={58} delay={5}>Des actifs financés, exposés aux aléas</Title>
      <div style={{ display: 'flex', gap: 30, marginTop: 50 }}>
        {EVENTS.map((e, i) => (
          <Card key={e.k} delay={25 + i * 35} accent={e.c} style={{ flex: 1 }}>
            <div style={{ fontSize: 22, color: e.c, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' }}>{e.k}</div>
            <div style={{ fontSize: 34, fontWeight: 700, marginTop: 8 }}>{e.y}</div>
            <div style={{ fontSize: 24, color: C.mist, marginTop: 12, lineHeight: 1.4 }}>{e.d}</div>
          </Card>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 30, marginTop: 36, alignItems: 'stretch' }}>
        <Card delay={240} accent={C.teal} style={{ flex: 1.4 }}>
          <div style={{ fontSize: 22, color: C.teal, fontWeight: 700, letterSpacing: 2 }}>BANQUE CENTRALE DE TUNISIE · NOV. 2026 · SELON LA PRESSE</div>
          <div style={{ fontSize: 34, fontWeight: 700, marginTop: 8 }}>Feuille de route finance verte & risques climatiques 2026-2030</div>
          <div style={{ fontSize: 22, color: C.mist, marginTop: 10 }}>Issue du projet d’assistance technique BCT–KfW · 4 piliers</div>
        </Card>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 18, opacity: s }}>
          <div style={{ padding: '18px 26px', borderRadius: 16, border: `2px solid ${C.amber}`, color: C.white, fontSize: 30, fontWeight: 700 }}>Risque bancaire</div>
          <div style={{ fontSize: 44, color: C.amber, fontWeight: 800 }}>×</div>
          <div style={{ padding: '18px 26px', borderRadius: 16, border: `2px solid ${C.teal}`, color: C.white, fontSize: 30, fontWeight: 700 }}>Climat</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
