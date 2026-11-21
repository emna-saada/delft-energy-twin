import React from 'react';
import { AbsoluteFill, OffthreadVideo, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { C, FONT } from '../theme';
import type { Props } from '../types';
import { Title } from './common';

export const Showcase: React.FC<Props> = () => {
  const frame = useCurrentFrame();
  const z = interpolate(frame, [0, 40], [0.9, 1], { extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ padding: '120px 150px 150px 150px', fontFamily: FONT, alignItems: 'center' }}>
      <Title size={46} delay={0}>Le tableau de bord, en direct</Title>
      <div style={{ marginTop: 24, width: 1500, borderRadius: 18, overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.45)',
        border: '1px solid rgba(255,255,255,0.18)', transform: `scale(${z})` }}>
        <div style={{ height: 40, background: '#E9E6DF', display: 'flex', alignItems: 'center', gap: 8, padding: '0 16px' }}>
          {['#E2683C', '#F7A456', '#12808F'].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />)}
          <div style={{ marginLeft: 18, fontSize: 17, color: C.muted }}>localhost:8501 · ClimaRisk Tunisie</div>
        </div>
        <OffthreadVideo src={staticFile('capture/dashboard.mp4')} startFrom={60} muted style={{ width: 1500, display: 'block' }} />
      </div>
    </AbsoluteFill>
  );
};
