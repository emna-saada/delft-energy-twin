export type Scene = { id: string; text: string; audio: string; audioSeconds: number; durationInFrames: number };
export type Props = {
  fps: number;
  scenes: Scene[];
  svg: { w: number; h: number; paths: { name: string; d: string; el_bp: number; heat: number }[];
         points: { x: number; y: number; r: number; s0: number; s1: number }[] };
  kpi: Record<string, number>;
  periods: { key: string; label: string; med: number; p10: number; p90: number; share: number }[];
  heatmap: { rows: string[]; cols: string[]; values: number[][] };
  disclaimer: string;
};
