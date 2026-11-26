import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { useGame } from './Game.jsx';

const LINES = ['Loading wetland videos', 'Calibrating Sentinel-2', 'Growing roof planes', 'Waking the agent'];

/** Short "boot screen": counts to 100, then lifts away. Click or any key skips it. */
export default function Loader({ onDone }) {
  const root = useRef(null);
  const [n, setN] = useState(0);
  const [gone, setGone] = useState(false);
  const { unlock } = useGame();

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const counter = { v: 0 };
    const tl = gsap.timeline({
      onComplete: () => {
        setGone(true);
        onDone();
        unlock('start');
      }
    });
    tl.to(counter, { v: 100, duration: reduced ? 0.1 : 1.7, ease: 'power2.inOut', onUpdate: () => setN(Math.round(counter.v)) })
      .to('.loader__inner', { y: -30, opacity: 0, duration: 0.35, ease: 'power2.in' })
      .to(root.current, { yPercent: -100, duration: reduced ? 0.1 : 0.9, ease: 'expo.inOut' }, '-=0.1');

    const skip = () => tl.progress() < 0.75 && tl.progress(0.75);
    window.addEventListener('keydown', skip);
    root.current.addEventListener('click', skip);
    return () => {
      window.removeEventListener('keydown', skip);
      tl.kill();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (gone) return null;
  return (
    <div className="loader" ref={root} role="status" aria-label="Loading">
      <div className="loader__inner">
        <div className="loader__box">
          <span className="loader__tag">emna · researcher {(0.5 + n / 200).toFixed(2)}</span>
          <span className="loader__num">{String(n).padStart(3, '0')}</span>
        </div>
        <div className="loader__bar">
          <span style={{ width: `${n}%` }} />
        </div>
        <p className="loader__line">{LINES[Math.min(LINES.length - 1, Math.floor(n / 25))]}…</p>
        <p className="loader__hint">Press any key to skip</p>
      </div>
    </div>
  );
}
