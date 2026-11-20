import React from 'react';
import { AbsoluteFill } from 'remotion';
import { C, FONT } from '../theme';
import type { Props } from '../types';
import { Title, useAppear } from './common';

export const Outro: React.FC<Props> = () => {
  const a = useAppear(60); const b = useAppear(150);
  return (
    <AbsoluteFill style={{ padding: '0 140px', justifyContent: 'center', fontFamily: FONT }}>
      <div style={{ display: 'inline-block', padding: '10px 22px', borderRadius: 12, background: 'rgba(217,119,6,0.18)',
        border: `1px solid ${C.amber}`, color: '#FBD38D', fontSize: 28, fontWeight: 600, alignSelf: 'flex-start' }}>
        Illustratif — à calibrer sur des données bancaires réelles
      </div>
      <div style={{ marginTop: 40 }}><Title size={96} delay={20}>ClimaRisk <span style={{ color: C.amber }}>Tunisie</span></Title></div>
      <div style={{ marginTop: 18, fontSize: 34, color: C.mist, opacity: a }}>Des pixels satellites aux indicateurs de risque de crédit</div>
      <div style={{ marginTop: 60, opacity: b, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ fontSize: 40, color: C.white, fontWeight: 700 }}>Emna Saada</div>
        <div style={{ fontSize: 30, color: C.mist }}>Géoinformatique, MSE — Université de la Manouba</div>
        <div style={{ fontSize: 28, color: '#9FE3EA', fontFamily: '"JetBrains Mono"' }}>github.com/emna-saada/climarisk-tunisia (à publier) · code MIT · données ouvertes</div>
      </div>
    </AbsoluteFill>
  );
};
