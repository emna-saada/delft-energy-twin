import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { achievements } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

const GameCtx = createContext(null);

export function GameProvider({ lenis, children }) {
  const [unlocked, setUnlocked] = useState([]);
  const [toasts, setToasts] = useState([]);
  const seen = useRef(new Set());

  const unlock = useCallback(id => {
    if (seen.current.has(id) || !achievements[id]) return;
    seen.current.add(id);
    setUnlocked(u => [...u, id]);
    const key = id + Date.now();
    setToasts(t => [...t, { key, id }]);
    setTimeout(() => setToasts(t => t.filter(x => x.key !== key)), 3800);
  }, []);

  return (
    <GameCtx.Provider value={{ unlocked, unlock, lenis, total: Object.keys(achievements).length }}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map(({ key, id }) => (
          <div className="toast" key={key}>
            <span className="toast__icon" aria-hidden>
              <Trophy />
            </span>
            <span>
              <small>Achievement unlocked</small>
              <b>{achievements[id].t}</b>
              <em>{achievements[id].d}</em>
            </span>
          </div>
        ))}
      </div>
    </GameCtx.Provider>
  );
}

export const useGame = () => useContext(GameCtx);

/** Unlock an achievement the first time `ref` scrolls into view. */
export function useAchievementOnView(ref, id, start = 'top 60%') {
  const { unlock } = useGame();
  useEffect(() => {
    if (!ref.current) return;
    const st = ScrollTrigger.create({ trigger: ref.current, start, once: true, onEnter: () => unlock(id) });
    return () => st.kill();
  }, [ref, id, start, unlock]);
}

export function Trophy(props) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4Z" />
      <path d="M17 6h3v1a4 4 0 0 1-4 4M7 6H4v1a4 4 0 0 0 4 4" />
    </svg>
  );
}

/** Scroll to an anchor through Lenis so the smooth scroll and ScrollTrigger stay in sync. */
export function useScrollTo() {
  const { lenis } = useGame();
  return useCallback(
    target => {
      const el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) return;
      if (lenis) lenis.scrollTo(el, { offset: -10, duration: 1.4 });
      else el.scrollIntoView({ behavior: 'smooth' });
    },
    [lenis]
  );
}
