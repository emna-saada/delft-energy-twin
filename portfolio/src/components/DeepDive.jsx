import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { useGame } from './Game.jsx';

const Ctx = createContext(null);

export function DeepDiveProvider({ children }) {
  const [project, setProject] = useState(null);
  const { unlock } = useGame();
  const open = useCallback(
    p => {
      setProject(p);
      unlock('curious');
    },
    [unlock]
  );
  return <Ctx.Provider value={{ project, open, close: () => setProject(null) }}>{children}</Ctx.Provider>;
}

export const useDeepDive = () => useContext(Ctx);

const TABS = [
  { id: 'how', label: 'How it works' },
  { id: 'links', label: 'Code & demos' },
  { id: 'refs', label: 'References' }
];

/** Side drawer with three angles on a project: method, code, and the literature behind it. */
export default function DeepDive() {
  const { project, close } = useDeepDive();
  const { lenis } = useGame();
  const [tab, setTab] = useState('how');
  const panel = useRef(null);
  const veil = useRef(null);

  useEffect(() => {
    if (!project) return;
    setTab('how');
    lenis?.stop();
    gsap.fromTo(veil.current, { opacity: 0 }, { opacity: 1, duration: 0.3 });
    gsap.fromTo(panel.current, { xPercent: 100 }, { xPercent: 0, duration: 0.6, ease: 'expo.out' });
    const onKey = e => e.key === 'Escape' && shut();
    window.addEventListener('keydown', onKey);
    panel.current.focus();
    return () => {
      window.removeEventListener('keydown', onKey);
      lenis?.start();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  useEffect(() => {
    if (!project) return;
    gsap.fromTo('.dive__pane > *', { y: 14, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.05, duration: 0.4, ease: 'power2.out' });
  }, [tab, project]);

  const shut = () => {
    gsap.to(veil.current, { opacity: 0, duration: 0.25 });
    gsap.to(panel.current, { xPercent: 100, duration: 0.4, ease: 'power3.in', onComplete: close });
  };

  if (!project) return null;
  const d = project.deep;
  return (
    <div className="dive" role="dialog" aria-modal="true" aria-label={`${project.title}: deep dive`}>
      <div className="dive__veil" ref={veil} onClick={shut} />
      <div className="dive__panel" ref={panel} tabIndex={-1} data-lenis-prevent>
        <div className="dive__head">
          <span className="eyebrow">Deep dive · {project.num}</span>
          <button className="dive__close" onClick={shut} aria-label="Close">
            ✕
          </button>
        </div>
        <h3 className="dive__title">{project.title}</h3>
        <p className="dive__sub">{project.subtitle}</p>
        <div className="tabs" role="tablist">
          {TABS.map(t => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'is-on' : ''} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="dive__pane">
          {tab === 'how' &&
            d.how.map((p, i) => (
              <div className="dive__step" key={i}>
                <span>{String(i + 1).padStart(2, '0')}</span>
                <p>{p}</p>
              </div>
            ))}
          {tab === 'links' && (
            <>
              {d.links.map(l => (
                <a key={l.href} className="dive__link" href={l.href} target="_blank" rel="noreferrer">
                  <span className="dive__link-kind">{l.kind === 'code' ? '</>' : '◉'}</span>
                  <span>
                    <b>{l.label}</b>
                    <small>{l.href.replace('https://', '')}</small>
                  </span>
                  <span aria-hidden>↗</span>
                </a>
              ))}
              {project.team && <p className="dive__note">{project.team}</p>}
              <div className="chips">
                {project.stack.map(s => (
                  <span className="chip" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {tab === 'refs' &&
            d.refs.map(r => (
              <a key={r.t} className="dive__ref" href={r.href} target="_blank" rel="noreferrer">
                <span className="dive__role">{r.role}</span>
                <span>{r.t}</span>
                <span aria-hidden>↗</span>
              </a>
            ))}
        </div>
      </div>
    </div>
  );
}
