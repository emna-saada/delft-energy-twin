import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SpotlightCard from '../bits/SpotlightCard.jsx';
import { SectionHead, useReveal } from '../components/ui.jsx';
import { awards, coursework, education, languages, method, skills, topGrades } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

function MethodWheel() {
  const wheel = useRef(null);
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = gsap.to(wheel.current, {
      rotate: -270,
      svgOrigin: '150 150',
      ease: 'none',
      scrollTrigger: {
        trigger: wheel.current.closest('.method'),
        start: 'top 75%',
        end: 'bottom 35%',
        scrub: 0.5,
        onUpdate: self => setStep(Math.min(3, Math.floor(self.progress * 4)))
      }
    });
    return () => t.scrollTrigger?.kill();
  }, []);

  const R = 120;
  const arc = i => {
    const a0 = (i * 90 - 90 + 3) * (Math.PI / 180);
    const a1 = ((i + 1) * 90 - 90 - 3) * (Math.PI / 180);
    const p = (a, r) => `${150 + r * Math.cos(a)} ${150 + r * Math.sin(a)}`;
    return `M${p(a0, R)} A${R} ${R} 0 0 1 ${p(a1, R)} L${p(a1, 64)} A64 64 0 0 0 ${p(a0, 64)}Z`;
  };

  return (
    <div className="method">
      <ol className="method__list">
        {method.map((m, i) => (
          <li key={m.n} className={i === step ? 'is-on' : ''}>
            <span>{m.n}</span>
            <div>
              <b>{m.t}</b>
              <p>{m.d}</p>
            </div>
          </li>
        ))}
      </ol>
      <svg className="method__wheel" viewBox="0 0 300 300" aria-hidden>
        <g ref={wheel}>
          {method.map((m, i) => {
            const mid = (i * 90 - 45) * (Math.PI / 180);
            return (
              <g key={m.n}>
                <path d={arc(i)} className={i === step ? 'seg is-on' : 'seg'} />
                <text x={150 + 92 * Math.cos(mid)} y={150 + 92 * Math.sin(mid)} textAnchor="middle" dominantBaseline="middle" transform={`rotate(${i * 90 - 45 + 90} ${150 + 92 * Math.cos(mid)} ${150 + 92 * Math.sin(mid)})`}>
                  {m.t.toUpperCase()}
                </text>
              </g>
            );
          })}
        </g>
        <circle cx="150" cy="150" r="52" className="hub" />
        <rect x="128" y="132" width="44" height="36" rx="3" fill="none" stroke="#19d3c5" strokeWidth="3" />
        <circle cx="150" cy="150" r="5" fill="#ff4f7b" />
      </svg>
    </div>
  );
}

export default function Skills() {
  const root = useReveal();
  return (
    <section className="skills" id="skills" ref={root}>
      <div className="wrap">
        <SectionHead eyebrow="Inventory · chapter 07" title="Tools in my" accent="backpack." />
        <div className="skills__grid">
          {skills.map(g => (
            <div data-reveal key={g.group}>
              <SpotlightCard className="scard" spotlightColor="rgba(58, 63, 224, 0.16)" theme="paper">
                <h4>{g.group}</h4>
                <div className="chips">
                  {g.items.map(s => (
                    <span className="chip" key={s}>
                      {s}
                    </span>
                  ))}
                </div>
              </SpotlightCard>
            </div>
          ))}
        </div>

        <div className="skills__split">
          <div data-reveal>
            <div className="shead__eyebrow">
              <span>My method</span>
              <i />
            </div>
            <p className="big-quote serif">“A result I can’t reproduce or defend with a test is a hypothesis, not a finding.”</p>
          </div>
          <div data-reveal>
            <MethodWheel />
          </div>
        </div>

        <div className="skills__bottom">
          <div data-reveal>
            <div className="shead__eyebrow">
              <span>Education</span>
              <i />
            </div>
            {education.map(e => (
              <div className="edu" key={e.title}>
                <span className="edu__when">{e.when}</span>
                <div>
                  <h4>{e.title}</h4>
                  <p>{e.org}</p>
                  <p className="muted">{e.note}</p>
                </div>
              </div>
            ))}
            <div className="grades">
              {topGrades.map(g => (
                <div key={g.c}>
                  <b>{g.g}</b>
                  <span>{g.c}</span>
                </div>
              ))}
            </div>
            <div className="chips">
              {coursework.map(c => (
                <span className="chip chip--soft" key={c}>
                  {c}
                </span>
              ))}
            </div>
            <div className="shead__eyebrow" style={{ marginTop: '2.2rem' }}>
              <span>Languages</span>
              <i />
            </div>
            <div className="langs">
              {languages.map(l => (
                <div key={l.l} className={l.p ? '' : 'is-studied'}>
                  <span>
                    {l.l} <small>{l.lv}</small>
                  </span>
                  <i>{l.p ? <b style={{ width: `${l.p}%` }} /> : <em>{l.note}</em>}</i>
                  {l.p && l.note ? <small className="langs__note">{l.note}</small> : null}
                </div>
              ))}
            </div>
          </div>
          <div data-reveal>
            <div className="shead__eyebrow">
              <span>Trophies & guild</span>
              <i />
            </div>
            <div className="trophies">
              {awards.map((a, i) => (
                <div className="trophy" key={a.t}>
                  <span className="trophy__n">{String(i + 1).padStart(2, '0')}</span>
                  <div>
                    <b>{a.t}</b>
                    <p>{a.d}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
