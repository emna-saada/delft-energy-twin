import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Trophy, useGame, useScrollTo } from './Game.jsx';

gsap.registerPlugin(ScrollTrigger);

/** Fixed left rail: logo, vertical tagline, XP bar (scroll progress) and trophy counter. */
export default function SideRail() {
  const fill = useRef(null);
  const { unlocked, total } = useGame();
  const go = useScrollTo();

  useEffect(() => {
    const st = ScrollTrigger.create({
      start: 0,
      end: 'max',
      onUpdate: self => gsap.set(fill.current, { scaleY: self.progress })
    });
    return () => st.kill();
  }, []);

  return (
    <aside className="rail" aria-label="Progress">
      <button className="rail__logo" onClick={() => go('#top')} aria-label="Back to top">
        <svg viewBox="0 0 32 32" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.2">
          <rect x="5" y="6" width="22" height="20" rx="2" />
          <circle cx="16" cy="16" r="3.2" fill="currentColor" stroke="none" />
        </svg>
      </button>
      <span className="rail__text rail__text--top">Vision · Orbit · Cities</span>
      <div className="rail__xp" title="Story progress">
        <span className="rail__xp-label">XP</span>
        <span className="rail__xp-track">
          <span className="rail__xp-fill" ref={fill} />
        </span>
      </div>
      <span className="rail__text rail__text--status">
        <i className="dot" /> Open to a PFE · Feb 2027
      </span>
      <div className="rail__trophies" title="Achievements unlocked">
        <Trophy />
        <b>
          {unlocked.length}/{total}
        </b>
      </div>
    </aside>
  );
}
