import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, FONT, riskColor } from '../theme';
import type { Props } from '../types';

export const useAppear = (delay = 0, damping = 16) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping } });
};

export const Title: React.FC<{ children: React.ReactNode; delay?: number; size?: number; color?: string }> = ({
  children, delay = 0, size = 64, color = C.white }) => {
  const s = useAppear(delay);
  return (
    <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: size, color, lineHeight: 1.08, letterSpacing: -1,
      opacity: s, transform: `translateY(${interpolate(s, [0, 1], [30, 0])}px)` }}>{children}</div>
  );
};

export const Card: React.FC<{ delay: number; children: React.ReactNode; accent?: string; style?: React.CSSProperties }> = ({
  delay, children, accent = C.amber, style }) => {
  const s = useAppear(delay);
  return (
    <div style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.14)', borderTop: `4px solid ${accent}`,
      borderRadius: 18, padding: '26px 30px', fontFamily: FONT, color: C.white, opacity: s,
      transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px) scale(${interpolate(s, [0, 1], [0.96, 1])})`, ...style }}>
      {children}
    </div>
  );
};

/** Tunisia map: governorates + loans, colour morphs from today (t=0) to SSP5-8.5 2050 (t=1). */
export const TunisiaMap: React.FC<{ svg: Props['svg']; t: number; height: number; pointsOpacity?: number }> = ({
  svg, t, height, pointsOpacity = 1 }) => {
  const w = (svg.w / svg.h) * height;
  return (
    <svg width={w} height={height} viewBox={`0 0 ${svg.w} ${svg.h}`}>
      <defs>
        <filter id="glow"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      {svg.paths.map((p) => (
        <path key={p.name} d={p.d} fill={riskColor(0.08 + t * p.heat * 0.9)} stroke="rgba(255,255,255,0.7)" strokeWidth={1.2}
          opacity={0.92} />
      ))}
      <g opacity={pointsOpacity}>
        {svg.points.map((q, i) => {
          const v = q.s0 + (q.s1 - q.s0) * t;
          return <circle key={i} cx={q.x} cy={q.y} r={q.r} fill={riskColor(v * 1.6)} stroke={C.ink} strokeWidth={0.6} opacity={0.9} />;
        })}
      </g>
    </svg>
  );
};

export const Counter: React.FC<{ from: number; to: number; delay: number; dur?: number; decimals?: number; suffix?: string;
  size?: number; color?: string }> = ({ from, to, delay, dur = 45, decimals = 1, suffix = '', size = 110, color = C.white }) => {
  const frame = useCurrentFrame();
  const v = interpolate(frame, [delay, delay + dur], [from, to], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: (x) => 1 - Math.pow(1 - x, 3) });
  return (
    <span style={{ fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: size, color, fontVariantNumeric: 'tabular-nums' }}>
      {v.toFixed(decimals).replace('.', ',')}{suffix}
    </span>
  );
};
