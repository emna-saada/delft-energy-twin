import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Chips, SectionHead, useReveal } from '../components/ui.jsx';
import { experience } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

export default function Experience() {
  const root = useReveal();
  const line = useRef(null);
  useEffect(() => {
    const t = gsap.fromTo(
      line.current,
      { scaleY: 0 },
      { scaleY: 1, ease: 'none', scrollTrigger: { trigger: line.current.parentElement, start: 'top 70%', end: 'bottom 60%', scrub: true } }
    );
    return () => t.scrollTrigger?.kill();
  }, []);

  return (
    <section className="exp" id="experience" ref={root}>
      <div className="wrap">
        <SectionHead eyebrow="Experience · chapter 04" title="Where I earned" accent="my XP." />
        <div className="timeline">
          <span className="timeline__line" ref={line} />
          {experience.map(e => (
            <div className="tl" key={e.role} data-reveal>
              <div className="tl__when">
                <b>{e.when}</b>
                <span>{e.where}</span>
              </div>
              <i className="tl__node" />
              <div className="tl__body">
                <h4>
                  {e.role} · <span>{e.org}</span>
                </h4>
                <p>{e.text}</p>
                <Chips items={e.tags} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
