import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGame } from './Game.jsx';

gsap.registerPlugin(ScrollTrigger);

/* ------------------------------------------------------------------ */
/* Ichkeul: schematic lake, marsh shrinking over 20 seasonal composites */
/* ------------------------------------------------------------------ */
const MODELS = [
  { m: 'Random Forest', v: 0.514 },
  { m: 'U-Net ResNet-34', v: 0.573 },
  { m: 'AlphaEarth embeddings', v: 0.605 }
];

export function IchkeulViz() {
  const [k, setK] = useState(1);
  const [playing, setPlaying] = useState(false);
  const tween = useRef(null);
  const root = useRef(null);
  const { unlock } = useGame();

  const summer = k % 2 === 0;
  const year = Math.ceil(k / 2); // 1..10
  const marshPct = summer ? 100 - (18 * (year - 1)) / 9 : null;
  const marshScale = summer ? 0.82 + 0.18 * (marshPct / 100) : 1;
  const waterScale = summer ? 0.78 : 1;

  useEffect(() => {
    if (k === 20) unlock('orbit');
  }, [k, unlock]);

  const play = () => {
    tween.current?.kill();
    const o = { v: 1 };
    setPlaying(true);
    tween.current = gsap.to(o, {
      v: 20,
      duration: 6,
      ease: 'none',
      onUpdate: () => setK(Math.round(o.v)),
      onComplete: () => setPlaying(false)
    });
  };
  useEffect(() => () => tween.current?.kill(), []);

  useEffect(() => {
    const st = ScrollTrigger.create({ trigger: root.current, start: 'top 65%', once: true, onEnter: play });
    return () => st.kill();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="viz viz--ichkeul" ref={root}>
      <div className="viz__screen">
        <svg viewBox="0 0 400 260" role="img" aria-label="Schematic map: marsh ring around the lake shrinks in summer composites">
          <rect width="400" height="260" fill="#ffe9cc" />
          <g opacity="0.25" stroke="#8b7a55">
            {Array.from({ length: 12 }, (_, i) => (
              <path key={i} d={`M0 ${i * 24} H400`} strokeWidth="0.5" />
            ))}
          </g>
          <g style={{ transform: `scale(${marshScale})`, transformOrigin: '200px 130px', transition: 'transform .5s ease' }}>
            <path d="M80 130 C80 60 170 34 230 46 C310 60 340 100 330 150 C320 210 240 228 170 220 C110 214 80 180 80 130Z" fill="#7ea36b" />
          </g>
          <g style={{ transform: `scale(${waterScale})`, transformOrigin: '205px 132px', transition: 'transform .5s ease' }}>
            <path d="M112 130 C112 80 180 64 226 72 C286 82 304 110 298 146 C290 190 236 200 180 194 C136 190 112 166 112 130Z" fill="#2f7f86" />
          </g>
          <circle cx="292" cy="58" r="5" fill="#ff4f7b" />
          <text x="300" y="62" fontSize="10" fontFamily="JetBrains Mono, monospace" fill="#3a3a2a">
            Jebel Ichkeul
          </text>
        </svg>
        <div className="viz__hud">
          <span>
            Composite <b>{String(k).padStart(2, '0')}</b>/20
          </span>
          <span className={`pill ${summer ? 'pill--gold' : 'pill--teal'}`}>{summer ? 'summer' : 'winter'}</span>
        </div>
        <div className="viz__readout">
          {summer ? (
            <>
              <b>{marshPct.toFixed(0)}%</b> summer marsh vs year 1
            </>
          ) : (
            <>Wet season: water expands with rainfall</>
          )}
        </div>
      </div>
      <div className="viz__controls">
        <button className="btn btn--small btn--ink" onClick={play} disabled={playing}>
          {playing ? 'Playing…' : '▶ Play 10 years'}
        </button>
        <input type="range" min="1" max="20" value={k} onChange={e => setK(+e.target.value)} aria-label="Seasonal composite" />
      </div>
      <div className="viz__models">
        {MODELS.map(m => (
          <div key={m.m}>
            <span>{m.m}</span>
            <i style={{ width: `${(m.v / 0.65) * 100}%` }} />
            <b>{m.v.toFixed(3)}</b>
          </div>
        ))}
        <small>mIoU on a spatial-block split · schematic map, trend from the real analysis</small>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Delft: point cloud assembling into buildings as you scroll           */
/* ------------------------------------------------------------------ */
function makeCity() {
  const rnd = (s => () => ((s = (s * 16807) % 2147483647) / 2147483647))(7);
  const pts = [];
  const grid = [];
  for (let gx = 0; gx < 5; gx++) for (let gy = 0; gy < 4; gy++) if (rnd() > 0.15) grid.push([gx, gy]);
  grid.forEach(([gx, gy]) => {
    const w = 1.4 + rnd() * 0.9, d = 1.4 + rnd() * 0.9, h = 1 + rnd() * 2.6;
    const x0 = gx * 2.6 - 6.5, y0 = gy * 2.6 - 5;
    const gable = rnd() > 0.45;
    const facing = rnd(); // roof orientation drives the "solar" colour
    for (let i = 0; i < 150; i++) {
      const u = rnd(), v = rnd();
      let x, y, z, roof = false;
      if (i < 90) {
        x = x0 + u * w; y = y0 + v * d;
        z = h + (gable ? (0.5 - Math.abs(u - 0.5)) * 1.2 : 0);
        roof = true;
      } else {
        const side = i % 2;
        x = side ? x0 + u * w : x0; y = side ? y0 : y0 + u * d; z = v * h;
      }
      pts.push({ x, y, z, roof, h, facing: gable ? (u < 0.5 ? facing : 1 - facing) : 0.6, sx: (rnd() - 0.5) * 22, sy: (rnd() - 0.5) * 22, sz: rnd() * 8 });
    }
  });
  return pts;
}

export function DelftCloud() {
  const canvas = useRef(null);
  const wrap = useRef(null);
  const state = useRef({ p: 0, angle: 0.6 });
  const [stage, setStage] = useState(0);
  const { unlock } = useGame();

  useEffect(() => {
    const pts = makeCity();
    const c = canvas.current;
    const ctx = c.getContext('2d');
    let raf, w, h;
    const resize = () => {
      const r = c.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      w = r.width; h = r.height;
      c.width = w * dpr; c.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ease = t => t * t * (3 - 2 * t);

    const draw = () => {
      const s = state.current;
      if (!reduced) s.angle += 0.0025;
      const a = ease(Math.min(1, s.p / 0.55));
      const solar = Math.max(0, Math.min(1, (s.p - 0.6) / 0.3));
      ctx.clearRect(0, 0, w, h);
      const scale = Math.min(w, h) / 17;
      const cos = Math.cos(s.angle), sin = Math.sin(s.angle);
      for (const q of pts) {
        const x = q.sx + (q.x - q.sx) * a, y = q.sy + (q.y - q.sy) * a, z = q.sz + (q.z - q.sz) * a;
        const rx = x * cos - y * sin, ry = x * sin + y * cos;
        const px = w / 2 + (rx - ry) * 0.866 * scale;
        const py = h * 0.58 + (rx + ry) * 0.5 * scale - z * scale * 0.9;
        let col;
        if (q.roof && solar > 0) {
          const g = q.facing;
          col = `rgba(${Math.round(200 + 50 * g)}, ${Math.round(110 + 90 * g)}, ${Math.round(60 + 20 * g)}, ${0.35 + 0.6 * solar})`;
        } else {
          const t = q.z / 4;
          col = `hsla(${174 - t * 30}, 55%, ${42 + t * 22}%, ${0.25 + 0.55 * a})`;
        }
        ctx.fillStyle = col;
        const sz = q.roof && solar > 0 ? 2.1 : 1.6;
        ctx.fillRect(px, py, sz, sz);
      }
      raf = requestAnimationFrame(draw);
    };
    draw();

    const st = ScrollTrigger.create({
      trigger: wrap.current,
      start: 'top 80%',
      end: 'bottom 30%',
      scrub: true,
      onUpdate: self => {
        state.current.p = self.progress;
        const sg = self.progress < 0.3 ? 0 : self.progress < 0.62 ? 1 : 2;
        setStage(sg);
        if (sg === 2) unlock('city');
      }
    });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      st.kill();
    };
  }, [unlock]);

  const STAGES = [
    { t: '442 million points', d: 'AHN6 airborne LiDAR, 14 tiles' },
    { t: '31,400 buildings', d: 'roof planes by Numba region growing' },
    { t: 'Sun on every roof', d: '72-direction horizon scan, 0.5 m cells' }
  ];
  return (
    <div className="viz viz--delft" ref={wrap}>
      <div className="viz__screen viz__screen--dark">
        <canvas ref={canvas} aria-label="Animated point cloud assembling into buildings, roofs coloured by solar potential" role="img" />
        <div className="viz__hud viz__hud--dark">
          {STAGES.map((s, i) => (
            <span key={s.t} className={i === stage ? 'is-on' : ''}>
              {String(i + 1).padStart(2, '0')}
            </span>
          ))}
        </div>
        <div className="viz__readout viz__readout--dark" key={stage}>
          <b>{STAGES[stage].t}</b> {STAGES[stage].d}
        </div>
      </div>
      <p className="fine">Scroll to assemble · a schematic cloud, not the real tiles</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* GeoRAG: agent loop typed out in a terminal                          */
/* ------------------------------------------------------------------ */
const LINES = [
  ['dim', '$ georag ask "map open water around Ichkeul"'],
  ['teal', '› retrieve   BM25 + Qwen3 over 2,239 papers'],
  ['teal', '› graph      181-term knowledge graph: NDWI, water mask'],
  ['teal', '› write      workflow.py  (Sentinel-2)'],
  ['coral', '› run        sandbox … ✗ error in workflow'],
  ['teal', '› repair     reads traceback, patches code'],
  ['gold', '› run        sandbox … ✓'],
  ['gold', '› check      vs JRC Global Surface Water'],
  ['ok', '✓ benchmark  30/30 tasks · IoU 0.966']
];

export function GeoTerminal() {
  const root = useRef(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    let id;
    const st = ScrollTrigger.create({
      trigger: root.current,
      start: 'top 75%',
      once: true,
      onEnter: () => {
        let i = 0;
        id = setInterval(() => {
          i += 1;
          setN(i);
          if (i >= LINES.length) clearInterval(id);
        }, 520);
      }
    });
    return () => {
      st.kill();
      clearInterval(id);
    };
  }, []);
  return (
    <div className="viz viz--term" ref={root}>
      <div className="term">
        <div className="miniterm__bar">
          <i />
          <i />
          <i />
          <span>georag-copilot · local</span>
        </div>
        <pre>
          {LINES.slice(0, n).map(([c, l], i) => (
            <span key={i} className={`c-${c} term__line`}>
              {l}
              {'\n'}
            </span>
          ))}
          <span className="cursor">▍</span>
        </pre>
      </div>
      <p className="fine">Illustration of the agent loop; the scores are the project’s benchmark results.</p>
    </div>
  );
}
