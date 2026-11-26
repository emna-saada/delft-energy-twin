import { useLayoutEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { Flip } from 'gsap/Flip';
import SpotlightCard from '../bits/SpotlightCard.jsx';
import { useReveal } from '../components/ui.jsx';
import { filters, moreProjects } from '../data.js';

gsap.registerPlugin(Flip);

const ICONS = {
  cv: <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M9 12a3 3 0 1 0 6 0a3 3 0 1 0-6 0" />,
  eo: <path d="M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />,
  data: <path d="M4 19V9M10 19V5M16 19v-7M22 19H2" />,
  ai: <path d="M12 5a2 2 0 1 0 0 .1M5 19a2 2 0 1 0 0 .1M19 19a2 2 0 1 0 0 .1M12 7v4M12 11l-6 6M12 11l6 6" />
};

export default function MoreProjects() {
  const root = useReveal();
  const grid = useRef(null);
  const flipState = useRef(null);
  const [f, setF] = useState('all');

  const pick = id => {
    flipState.current = Flip.getState(grid.current.querySelectorAll('.mcard'));
    setF(id);
  };

  useLayoutEffect(() => {
    if (!flipState.current) return;
    Flip.from(flipState.current, {
      duration: 0.6,
      ease: 'power3.inOut',
      scale: true,
      absolute: true,
      onEnter: els => gsap.fromTo(els, { opacity: 0, scale: 0.85 }, { opacity: 1, scale: 1, duration: 0.5 }),
      onLeave: els => gsap.to(els, { opacity: 0, scale: 0.85, duration: 0.4 })
    });
    flipState.current = null;
  }, [f]);

  const shown = moreProjects.filter(p => f === 'all' || p.cat === f);

  return (
    <section className="more" id="more" ref={root}>
      <div className="wrap">
        <div className="more__head" data-reveal>
          <div className="shead__eyebrow">
            <span>Side quests</span>
            <i />
          </div>
          <div className="filters" role="tablist" aria-label="Filter projects">
            {filters.map(x => (
              <button key={x.id} role="tab" aria-selected={f === x.id} className={f === x.id ? 'is-on' : ''} onClick={() => pick(x.id)}>
                {x.label}
              </button>
            ))}
          </div>
        </div>
        <div className="more__grid" ref={grid}>
          {shown.map(p => (
            <SpotlightCard key={p.id} className="mcard" data-flip-id={p.id} spotlightColor="rgba(226, 88, 62, 0.16)" theme="paper">
              <div className="mcard__top">
                <span className="mcard__icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    {ICONS[p.cat]}
                  </svg>
                </span>
                <span className="mcard__tag">{p.tag}</span>
              </div>
              <h4>{p.title}</h4>
              <p>{p.text}</p>
              <ul>
                {p.bullets.map(b => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <div className="mcard__foot">
                <code>{p.stack}</code>
                <div className="mcard__links">
                  {p.links.map(l => (
                    <a key={l.label} href={l.href} target="_blank" rel="noreferrer">
                      {l.label} ↗
                    </a>
                  ))}
                  {p.refs.map(r => (
                    <a key={r.t} href={r.href} target="_blank" rel="noreferrer" className="mcard__ref" title={r.t}>
                      ref ↗
                    </a>
                  ))}
                </div>
              </div>
            </SpotlightCard>
          ))}
        </div>
      </div>
    </section>
  );
}
