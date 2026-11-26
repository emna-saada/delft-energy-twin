import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import DetectionScene from '../components/DetectionScene.jsx';
import { useAchievementOnView } from '../components/Game.jsx';
import { Chips } from '../components/ui.jsx';
import { domains } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

function PixelField() {
  // Seasonal satellite tiles: water (teal), marsh (green), dry (sand) shifting over time
  const cells = Array.from({ length: 16 * 10 }, (_, i) => {
    const x = i % 16, y = Math.floor(i / 16);
    const d = Math.hypot(x - 7.5, (y - 4.5) * 1.5);
    return { i, type: d < 3.2 ? 'w' : d < 5.2 ? 'm' : 'd', delay: (d * 0.12).toFixed(2) };
  });
  return (
    <div className="pixfield" aria-hidden>
      {cells.map(c => (
        <i key={c.i} className={`px px--${c.type}`} style={{ animationDelay: `${c.delay}s` }} />
      ))}
      <span className="pixfield__label">Sentinel-2 · composite 07/20</span>
    </div>
  );
}

function IsoPoints() {
  const pts = [];
  const blocks = [
    [40, 150, 60, 90], [120, 120, 50, 120], [190, 160, 70, 70], [280, 110, 55, 130], [350, 150, 60, 85]
  ];
  blocks.forEach(([x, y, w, h], b) => {
    for (let k = 0; k < 120; k++) {
      const u = (k * 37 % 100) / 100, v = (k * 61 % 100) / 100;
      pts.push({ x: x + u * w, y: y + v * h, roof: v < 0.18, b });
    }
  });
  return (
    <svg className="isopts" viewBox="0 0 440 300" aria-hidden>
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={p.roof ? 2.4 : 1.6} fill={p.roof ? '#e9b949' : `hsl(${172 + p.b * 6} 45% ${30 + p.b * 6}%)`} style={{ animationDelay: `${(i % 60) * 0.02}s` }} />
      ))}
      <text x="20" y="285" fontFamily="JetBrains Mono, monospace" fontSize="12" fill="#19d3c5">
        AHN6 · 442,000,000 points
      </text>
    </svg>
  );
}

function MiniTerminal() {
  return (
    <div className="miniterm" aria-hidden>
      <div className="miniterm__bar">
        <i />
        <i />
        <i />
        <span>georag</span>
      </div>
      <pre>
        <span className="c-dim">$</span> ask "summer water, Ichkeul"{'\n'}
        <span className="c-teal">› retrieve</span> BM25 + Qwen3{'\n'}
        <span className="c-teal">› write</span> workflow.py{'\n'}
        <span className="c-coral">› run ✗</span> error caught{'\n'}
        <span className="c-teal">› repair</span> patch applied{'\n'}
        <span className="c-gold">› run ✓</span> IoU 0.966{'\n'}
        <span className="cursor">▍</span>
      </pre>
    </div>
  );
}

const VISUALS = {
  cv: () => <DetectionScene running compact />,
  eo: PixelField,
  lidar: IsoPoints,
  ai: MiniTerminal
};

export default function Build() {
  const root = useRef(null);
  const [active, setActive] = useState(0);
  useAchievementOnView(root, 'build', 'top 30%');

  useEffect(() => {
    const mm = gsap.matchMedia();
    mm.add('(min-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
      const cards = gsap.utils.toArray('.build__card', root.current);
      gsap.set(cards.slice(1), { yPercent: 120, rotate: 6 });
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: 'top top',
          end: () => `+=${window.innerHeight * 2.4}`,
          pin: true,
          scrub: 0.6,
          snap: { snapTo: 1 / (cards.length - 1), duration: 0.5, ease: 'power2.inOut' },
          onUpdate: self => setActive(Math.round(self.progress * (cards.length - 1)))
        }
      });
      cards.forEach((card, i) => {
        if (i === 0) return;
        tl.to(card, { yPercent: 0, rotate: 0, ease: 'power2.out', duration: 1 }, i - 1).to(
          cards[i - 1],
          { scale: 0.9, yPercent: -6, opacity: 0.35, filter: 'blur(2px)', duration: 1 },
          i - 1
        );
      });
    });
    return () => mm.revert();
  }, []);

  const d = domains[active];
  return (
    <section className="build" id="build" ref={root}>
      <div className="build__inner">
        <div className="build__copy">
          <div className="shead__eyebrow">
            <span>What I build · chapter 02</span>
            <i />
          </div>
          <div className="build__count">
            <b key={active}>{String(active + 1).padStart(2, '0')}</b>
            <span>/ {String(domains.length).padStart(2, '0')}</span>
          </div>
          <div className="build__swap" key={d.key}>
            <p className="build__kicker serif">{d.kicker}</p>
            <h2 className="build__title">{d.title}</h2>
            <p className="build__text">{d.text}</p>
            <Chips items={d.tags} />
            <div className="build__stat">
              <b>{d.stat.value}</b>
              <span>{d.stat.label}</span>
            </div>
          </div>
          <div className="build__dots" aria-hidden>
            {domains.map((x, i) => (
              <i key={x.key} className={i === active ? 'is-on' : ''} />
            ))}
          </div>
        </div>

        <div className="build__deck">
          {domains.map((x, i) => {
            const V = VISUALS[x.key];
            return (
              <article className={`build__card build__card--${x.key}`} key={x.key}>
                <header>
                  <span>{String(i + 1).padStart(2, '0')}</span>
                  <b>{x.title}</b>
                </header>
                <div className="build__visual">
                  <V />
                </div>
                {/* Mobile fallback: text lives in the card */}
                <div className="build__mobile">
                  <p>{x.text}</p>
                  <div className="build__stat">
                    <b>{x.stat.value}</b>
                    <span>{x.stat.label}</span>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
