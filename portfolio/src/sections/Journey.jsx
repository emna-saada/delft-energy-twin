import { useEffect, useMemo, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SplitText from '../bits/SplitText.jsx';
import { useAchievementOnView } from '../components/Game.jsx';
import { journey, meters, phases } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

const STOP_W = 400; // px between stops on desktop
const LEAD = 0.26; // traveller sits at 26% of the viewport width
const AMP = 34; // road wave amplitude
const WAVE = STOP_W * 2; // wavelength: cards alternate above / below the road

const ICONS = {
  speech: 'M4 5h16v10H9l-5 4V5Z',
  globe: 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18',
  people: 'M8 11a3 3 0 1 0 0-6a3 3 0 0 0 0 6M16 11a3 3 0 1 0 0-6M2 20c0-3 3-5 6-5s6 2 6 5M14 15c3 0 6 2 6 5',
  spark: 'M12 2v6M12 16v6M2 12h6M16 12h6M5 5l4 4M15 15l4 4M19 5l-4 4M9 15l-4 4',
  mic: 'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3M5 11a7 7 0 0 0 14 0M12 18v3',
  school: 'M2 9l10-5 10 5-10 5L2 9ZM6 11v5c3 2 9 2 12 0v-5',
  ieee: 'M4 4h16v16H4zM8 8v8M12 8v8M16 8v8',
  flag: 'M5 21V4M5 4h12l-2 4 2 4H5',
  plane: 'M2 13l20-8-8 18-3-7-9-3Z',
  chip: 'M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4',
  board: 'M3 5h18v12H3zM8 21h8M12 17v4M7 9h4M7 13h7',
  trophy: 'M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4ZM17 6h3v1a4 4 0 0 1-4 4M7 6H4v1a4 4 0 0 0 4 4',
  lab: 'M9 3h6M10 3v6l-5 10a1 1 0 0 0 1 2h12a1 1 0 0 0 1-2l-5-10V3M7 15h10',
  target: 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10M12 11a1 1 0 1 0 0 2'
};

export function Icon({ name, size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={ICONS[name] || ICONS.target} />
    </svg>
  );
}

const roadY = (x, mid) => mid + AMP * Math.sin((2 * Math.PI * (x - STOP_W / 2)) / WAVE - Math.PI / 2);

/** Cumulative meter values after each stop, and the maximum for scaling. */
function useMeterTable() {
  return useMemo(() => {
    const acc = Object.fromEntries(meters.map(m => [m.key, 0]));
    const rows = journey.map(s => {
      for (const k in s.gains) acc[k] += s.gains[k];
      return { ...acc };
    });
    const max = Math.max(...meters.map(m => rows[rows.length - 1][m.key]));
    return { rows, max };
  }, []);
}

export default function Journey() {
  const root = useRef(null);
  const track = useRef(null);
  const road = useRef(null);
  const traveller = useRef(null);
  const [active, setActive] = useState(0);
  const [desktop, setDesktop] = useState(false);
  const { rows, max } = useMeterTable();
  useAchievementOnView(root, 'journey', 'top 40%');

  const trackW = journey.length * STOP_W + STOP_W;

  useEffect(() => {
    const mm = gsap.matchMedia();
    mm.add('(min-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
      setDesktop(true);
      const vw = () => window.innerWidth;
      const startX = () => vw() * LEAD - STOP_W / 2; // first stop under the traveller
      const endX = () => vw() * LEAD - (trackW - STOP_W * 1.5);
      const len = road.current.getTotalLength();
      gsap.set(road.current, { strokeDasharray: len, strokeDashoffset: len });
      // The SVG road is drawn in a 600-unit-high box stretched to the track height
      const scale = () => track.current.offsetHeight / 600;
      const setAmp = () => root.current.style.setProperty('--amp', `${AMP * scale()}px`);
      setAmp();

      const tween = gsap.fromTo(
        track.current,
        { x: startX },
        {
          x: endX,
          ease: 'none',
          scrollTrigger: {
            trigger: root.current,
            start: 'top top',
            end: () => `+=${trackW - STOP_W * 1.5}`,
            pin: true,
            scrub: 0.8,
            invalidateOnRefresh: true,
            onRefresh: setAmp,
            onUpdate: self => {
              const x = gsap.getProperty(track.current, 'x');
              const travelX = vw() * LEAD - x; // traveller position in track coordinates
              gsap.set(road.current, { strokeDashoffset: len * (1 - travelX / trackW) });
              gsap.set(traveller.current, { y: (roadY(travelX, 300) - 300) * scale() });
              const idx = Math.max(0, Math.min(journey.length - 1, Math.floor((travelX - STOP_W / 2 + STOP_W * 0.35) / STOP_W)));
              setActive(a => (a === idx ? a : idx));
              root.current.style.setProperty('--trip', self.progress.toFixed(3));
            }
          }
        }
      );
      return () => {
        tween.scrollTrigger?.kill();
        setDesktop(false);
      };
    });

    // Mobile / reduced motion: vertical road, one trigger per stop
    mm.add('(max-width: 899px), (prefers-reduced-motion: reduce)', () => {
      const triggers = gsap.utils.toArray('.stop', root.current).map((el, i) =>
        ScrollTrigger.create({ trigger: el, start: 'top 60%', end: 'bottom 60%', onToggle: s => s.isActive && setActive(i) })
      );
      gsap.utils.toArray('.stop', root.current).forEach(el =>
        gsap.from(el, { x: 40, opacity: 0, duration: 0.8, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 85%', once: true } })
      );
      return () => triggers.forEach(t => t.kill());
    });
    return () => mm.revert();
  }, [trackW]);

  const cur = journey[active];
  const ph = phases[cur.phase];
  const vals = rows[active];

  // Road path (sinusoid) in track coordinates
  const roadPath = useMemo(() => {
    const H = 600, mid = H / 2;
    let d = `M0 ${roadY(0, mid).toFixed(1)}`;
    for (let x = 10; x <= trackW; x += 10) d += ` L${x} ${roadY(x, mid).toFixed(1)}`;
    return d;
  }, [trackW]);

  return (
    <section className="journey" id="journey" ref={root} style={{ '--ph': ph.color }}>
      <div className="journey__bg" aria-hidden>
        <i className="blob blob--a" />
        <i className="blob blob--b" />
      </div>

      <div className="journey__hud">
        <div className="journey__intro">
          <div className="shead__eyebrow">
            <span>My journey · chapter 01</span>
            <i />
          </div>
          <h2 className="journey__title">
            <SplitText text="A tour of how" tag="span" splitType="words" mask delay={60} textAlign="left" className="shead__split" />{' '}
            <em className="serif">I built myself.</em>
          </h2>
        </div>
        <div className="journey__phase" key={cur.phase}>
          <span className="journey__phase-dot" />
          <b>{ph.label}</b>
          <em className="serif">{ph.sub}</em>
        </div>
        <div className="meters" role="list" aria-label="Skills gained so far">
          {meters.map(m => {
            const v = vals[m.key];
            const g = cur.gains[m.key];
            return (
              <div className="meter" role="listitem" key={m.key} style={{ '--mc': m.color }}>
                <span className="meter__label">
                  {m.label} <b>Lv {v}</b>
                  {g ? (
                    <i className="meter__plus" key={`${active}-${m.key}`}>
                      +{g}
                    </i>
                  ) : null}
                </span>
                <span className="meter__track">
                  <span className="meter__fill" style={{ width: `${(v / max) * 100}%` }} />
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="journey__viewport">
        <div className="journey__track" ref={track} style={{ '--track-w': `${trackW}px` }}>
          {(
            <svg className="journey__road" width={trackW} height="600" viewBox={`0 0 ${trackW} 600`} preserveAspectRatio="none" aria-hidden>
              <path d={roadPath} className="road road--base" />
              <path d={roadPath} className="road road--lane" />
              <path d={roadPath} className="road road--done" ref={road} />
            </svg>
          )}
          {journey.map((s, i) => {
            const p = phases[s.phase];
            const up = i % 2 === 0;
            return (
              <article
                key={s.title}
                className={`stop ${up ? 'stop--up' : 'stop--down'} ${i <= active ? 'is-passed' : ''} ${i === active ? 'is-active' : ''} ${s.next ? 'stop--next' : ''}`}
                style={{ '--pc': p.color, '--left': `${STOP_W / 2 + i * STOP_W}px` }}
              >
                <span className="stop__node" aria-hidden />
                <div className="stop__card">
                  <div className="stop__top">
                    <span className="stop__icon">
                      <Icon name={s.icon} />
                    </span>
                    <span className="stop__when">{s.when}</span>
                    <span className="stop__n">{String(i + 1).padStart(2, '0')}</span>
                  </div>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                  <div className="stop__foot">
                    <span className="stop__gain">{s.gain}</span>
                    {s.cert && (
                      <a href={s.cert} target="_blank" rel="noreferrer" className="stop__cert">
                        Certificate ↗
                      </a>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
        {(
          <div className="traveller" ref={traveller} aria-hidden>
            <span className="traveller__ring" />
            <b>ES</b>
            <span className="traveller__tag">
              {String(active + 1).padStart(2, '0')}/{journey.length}
            </span>
          </div>
        )}
      </div>
      {desktop && <p className="journey__hint">Keep scrolling: the road moves, the meters level up</p>}
    </section>
  );
}
