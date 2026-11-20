import React from 'react';
import { Composition, staticFile } from 'remotion';
import { Main } from './Main';
import type { Props } from './types';
import defaultProps from '../public/props.json';

export const RemotionRoot: React.FC = () => {
  const p = defaultProps as unknown as Props;
  const total = p.scenes.reduce((s, x) => s + x.durationInFrames, 0);
  return (
    <Composition id="ClimaRisk" component={Main as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={total} fps={p.fps} width={1920} height={1080}
      defaultProps={p as unknown as Record<string, unknown>}
      calculateMetadata={({ props }) => {
        const q = props as unknown as Props;
        return { durationInFrames: q.scenes.reduce((s, x) => s + x.durationInFrames, 0) };
      }} />
  );
};
void staticFile;
