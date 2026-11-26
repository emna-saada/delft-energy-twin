import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

// Illustrative birds with a box, behaviour label and a made-up confidence for the animation.
const BIRDS = [
  { id: 'heron', box: [92, 168, 120, 190], label: 'walking', conf: 0.93 },
  { id: 'flamingo', box: [340, 196, 150, 160], label: 'feeding', conf: 0.88 },
  { id: 'duck', box: [560, 300, 110, 62], label: 'swimming', conf: 0.91 },
  { id: 'flyer', box: [470, 70, 140, 70], label: 'flying', conf: 0.86 },
  { id: 'egret', box: [690, 214, 70, 96], label: 'preening', conf: 0.79 }
];

function Birds() {
  return (
    <g className="birds">
      {/* grey heron, walking */}
      <g className="bird bird--heron" transform="translate(150 250)">
        <path d="M-30 20 Q0 -6 34 10 Q20 34 -18 34 Z" fill="#5d6b70" />
        <path d="M24 8 Q34 -40 14 -66 Q8 -76 20 -82" stroke="#5d6b70" strokeWidth="7" fill="none" strokeLinecap="round" />
        <path d="M20 -82 L46 -78" stroke="#c8962f" strokeWidth="4" strokeLinecap="round" />
        <path d="M-4 32 L-10 96 M8 32 L18 96" stroke="#3b4548" strokeWidth="3" />
      </g>
      {/* flamingo, feeding (head down) */}
      <g className="bird bird--flamingo" transform="translate(410 270)">
        <ellipse cx="0" cy="0" rx="38" ry="22" fill="#ef8f86" />
        <path d="M30 -6 Q58 -40 46 -2 Q40 30 52 52" stroke="#ef8f86" strokeWidth="7" fill="none" strokeLinecap="round" />
        <path d="M50 52 l10 8" stroke="#2a2a2a" strokeWidth="5" strokeLinecap="round" />
        <path d="M-6 20 L-10 80 M8 20 L16 80" stroke="#e07a70" strokeWidth="3" />
      </g>
      {/* duck, swimming */}
      <g className="bird bird--duck" transform="translate(612 336)">
        <path d="M-40 0 Q-30 -26 10 -16 Q30 -40 46 -22 Q50 -10 36 -6 Q40 14 -4 14 Q-36 14 -40 0Z" fill="#3e5a4f" />
        <path d="M46 -22 l14 4 l-12 6" fill="#c8962f" />
      </g>
      {/* flying bird */}
      <g className="bird bird--flyer" transform="translate(540 104)">
        <path className="wing" d="M0 0 Q-34 -26 -66 -8 Q-30 -10 0 6 Q30 -10 66 -8 Q34 -26 0 0Z" fill="#2c3b3f" />
      </g>
      {/* egret, preening */}
      <g className="bird bird--egret" transform="translate(724 270)">
        <ellipse cx="0" cy="0" rx="20" ry="14" fill="#f4f1ea" />
        <path d="M12 -4 Q26 -30 10 -40 Q0 -44 4 -22" stroke="#f4f1ea" strokeWidth="5" fill="none" strokeLinecap="round" />
        <path d="M-4 12 L-6 40 M4 12 L8 40" stroke="#2a2a2a" strokeWidth="2" />
      </g>
    </g>
  );
}

/**
 * Wetland scene with a "Run detector" state. `auto` loops scanning on its own (hero lens).
 * Shows how a detector reads a frame; it is an illustration, not a dataset frame.
 */
export default function DetectionScene({ auto = false, running: runningProp, compact = false }) {
  const root = useRef(null);
  const [runningAuto, setRunningAuto] = useState(false);
  const running = runningProp ?? runningAuto;

  useEffect(() => {
    if (!auto) return;
    let on = false;
    const id = setInterval(() => {
      on = !on;
      setRunningAuto(on);
    }, 3200);
    const first = setTimeout(() => setRunningAuto(true), 900);
    return () => {
      clearInterval(id);
      clearTimeout(first);
    };
  }, [auto]);

  useEffect(() => {
    const q = gsap.utils.selector(root);
    if (running) {
      const tl = gsap.timeline();
      tl.fromTo(q('.scanline'), { attr: { x: -40 }, opacity: 1 }, { attr: { x: 820 }, duration: 1.1, ease: 'power1.inOut' })
        .to(q('.scanline'), { opacity: 0, duration: 0.2 })
        .fromTo(
          q('.det'),
          { opacity: 0, scale: 1.25, transformOrigin: '50% 50%' },
          { opacity: 1, scale: 1, duration: 0.45, ease: 'back.out(2)', stagger: 0.12 },
          0.25
        );
      return () => tl.kill();
    }
    gsap.to(q('.det'), { opacity: 0, duration: 0.3 });
  }, [running]);

  return (
    <svg ref={root} className={`scene ${compact ? 'scene--compact' : ''}`} viewBox="0 0 800 450" preserveAspectRatio={compact ? 'xMidYMid slice' : 'xMidYMid meet'} role="img" aria-label="Illustrated wetland with birds and detection boxes">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f6d9a8" />
          <stop offset="0.55" stopColor="#f2b48f" />
          <stop offset="1" stopColor="#e9a08a" />
        </linearGradient>
        <linearGradient id="water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5f9c96" />
          <stop offset="1" stopColor="#1d4f50" />
        </linearGradient>
      </defs>
      <rect width="800" height="450" fill="url(#sky)" />
      <circle cx="640" cy="150" r="46" fill="#fbe7c2" opacity="0.9" />
      <path d="M0 230 Q120 190 240 214 T480 206 T800 210 V260 H0Z" fill="#8a9c86" opacity="0.65" />
      <path d="M0 246 Q200 226 400 240 T800 236 V270 H0Z" fill="#6c8471" opacity="0.8" />
      <rect y="262" width="800" height="188" fill="url(#water)" />
      <g stroke="#cfe6df" strokeWidth="2" opacity="0.35" className="ripples">
        <path d="M60 300 h80 M250 330 h60 M520 380 h90 M120 400 h50 M680 320 h60 M360 420 h70" />
      </g>
      <Birds />
      <g className="reeds" stroke="#3f5a3c" strokeWidth="3" strokeLinecap="round">
        {Array.from({ length: 26 }, (_, i) => {
          const x = i * 31 + (i % 3) * 7;
          const h = 60 + ((i * 37) % 50);
          return <path key={i} d={`M${x} 452 Q${x + 6} ${452 - h / 2} ${x + 12 - (i % 2) * 20} ${452 - h}`} fill="none" />;
        })}
      </g>
      <rect className="scanline" x="-40" y="0" width="6" height="450" fill="#57d6bf" opacity="0" />
      {BIRDS.map(b => {
        const [x, y, w, h] = b.box;
        const tag = `${b.label} ${b.conf.toFixed(2)}`;
        return (
          <g className="det" key={b.id} opacity="0">
            <rect x={x} y={y} width={w} height={h} fill="none" stroke="#57d6bf" strokeWidth="3" rx="3" />
            <rect x={x - 1.5} y={y - 24} width={tag.length * 8.6 + 14} height="24" fill="#0a2e30" rx="3" />
            <text x={x + 6} y={y - 7} fill="#57d6bf" fontFamily="JetBrains Mono, monospace" fontSize="14">
              {tag}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
