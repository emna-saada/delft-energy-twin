export const C = {
  ink: '#0F2A33', petrol: '#0E5E6F', teal: '#12808F', sand: '#F6F4EF', muted: '#5B6B70',
  border: '#E3E0D8', amber: '#D97706', red: '#B8323B', white: '#FFFFFF', mist: '#D5E6EA',
};
export const RISK = ['#FFF4D6', '#FDD58A', '#F7A456', '#E2683C', '#B8323B', '#6E1434'];
export const FONT = 'Inter, "Fira Sans", sans-serif';
export const MONO = '"JetBrains Mono", "Fira Code", monospace';

const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export function riskColor(v: number): string {
  const x = Math.max(0, Math.min(1, v)) * (RISK.length - 1);
  const i = Math.min(Math.floor(x), RISK.length - 2);
  const f = x - i;
  const a = hex(RISK[i]); const b = hex(RISK[i + 1]);
  const c = a.map((ai, k) => Math.round(ai + (b[k] - ai) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
