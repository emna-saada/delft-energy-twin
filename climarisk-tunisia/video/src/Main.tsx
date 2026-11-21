import React from 'react';
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, FONT } from './theme';
import type { Props, Scene } from './types';
import { Hook } from './scenes/Hook';
import { Origin } from './scenes/Origin';
import { Regulation } from './scenes/Regulation';
import { Method } from './scenes/Method';
import { Results } from './scenes/Results';
import { Showcase } from './scenes/Showcase';
import { Outro } from './scenes/Outro';

const LABELS: Record<string, string> = {
  hook: 'Accroche', origin: "L'origine de l'idée", regulation: 'Cadre réglementaire', method: 'Données et méthode',
  results: 'Résultats', showcase: 'Tableau de bord', outro: 'Limites et suite',
};

const Captions: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const parts = scene.text.replace(/ : /g, ' : |').replace(/\. /g, '.|').split('|').map((s) => s.trim()).filter(Boolean);
  const total = parts.reduce((s, p) => s + p.length, 0);
  let t = 0.6;
  const t_now = frame / fps;
  let current = '';
  for (const p of parts) {
    const d = (scene.audioSeconds * p.length) / total;
    if (t_now >= t && t_now < t + d) current = p;
    t += d;
  }
  if (!current) return null;
  return (
    <div style={{ position: 'absolute', bottom: 46, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
      <div style={{ maxWidth: 1400, background: 'rgba(15,42,51,0.82)', color: C.white, fontFamily: FONT, fontSize: 30,
        lineHeight: 1.35, padding: '12px 26px', borderRadius: 14, textAlign: 'center' }}>{current}</div>
    </div>
  );
};

const Chip: React.FC<{ i: number; id: string }> = ({ i, id }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 18 } });
  return (
    <div style={{ position: 'absolute', top: 40, left: 56, display: 'flex', alignItems: 'center', gap: 14,
      fontFamily: FONT, opacity: s, transform: `translateY(${interpolate(s, [0, 1], [-20, 0])}px)` }}>
      <div style={{ fontWeight: 700, color: C.amber, fontSize: 22, letterSpacing: 2 }}>{String(i + 1).padStart(2, '0')}</div>
      <div style={{ width: 40, height: 2, background: C.amber }} />
      <div style={{ color: C.mist, fontSize: 22, letterSpacing: 3, textTransform: 'uppercase', fontWeight: 600 }}>{LABELS[id]}</div>
    </div>
  );
};

const Brand: React.FC = () => (
  <div style={{ position: 'absolute', top: 40, right: 56, fontFamily: FONT, color: C.mist, fontSize: 20, fontWeight: 600,
    letterSpacing: 1 }}>ClimaRisk <span style={{ color: C.amber }}>Tunisie</span></div>
);

export const Main: React.FC<Props> = (props) => {
  const comps: Record<string, React.FC<Props>> = {
    hook: Hook, origin: Origin, regulation: Regulation, method: Method, results: Results, showcase: Showcase, outro: Outro,
  };
  let from = 0;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 120% at 85% 10%, #164B57 0%, ${C.ink} 55%, #0A1E25 100%)` }}>
      {props.scenes.map((sc, i) => {
        const S = comps[sc.id];
        const el = (
          <Sequence key={sc.id} from={from} durationInFrames={sc.durationInFrames} name={sc.id}>
            <Fade dur={sc.durationInFrames}><S {...props} /></Fade>
            <Audio src={staticFile(sc.audio)} startFrom={0} />
            <Chip i={i} id={sc.id} />
            <Brand />
            <Captions scene={sc} />
          </Sequence>
        );
        from += sc.durationInFrames;
        return el;
      })}
    </AbsoluteFill>
  );
};

const Fade: React.FC<{ dur: number; children: React.ReactNode }> = ({ dur, children }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 12, dur - 12, dur], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};
