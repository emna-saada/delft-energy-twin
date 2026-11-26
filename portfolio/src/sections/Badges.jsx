import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import CountUp from '../bits/CountUp.jsx';
import { useAchievementOnView } from '../components/Game.jsx';
import { SectionHead, useReveal } from '../components/ui.jsx';
import { badges } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

const MARK = { nvidia: 'DLI', google: 'G', giz: 'giz' };

function Badge({ b, i }) {
  const el = useRef(null);
  useEffect(() => {
    const node = el.current;
    if (!window.matchMedia('(hover: hover) and (prefers-reduced-motion: no-preference)').matches) return;
    const rx = gsap.quickTo(node, 'rotationX', { duration: 0.5, ease: 'power3' });
    const ry = gsap.quickTo(node, 'rotationY', { duration: 0.5, ease: 'power3' });
    const move = e => {
      const r = node.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      ry(px * 16);
      rx(-py * 16);
      node.style.setProperty('--mx', `${(px + 0.5) * 100}%`);
      node.style.setProperty('--my', `${(py + 0.5) * 100}%`);
    };
    const leave = () => {
      rx(0);
      ry(0);
    };
    node.addEventListener('pointermove', move);
    node.addEventListener('pointerleave', leave);
    return () => {
      node.removeEventListener('pointermove', move);
      node.removeEventListener('pointerleave', leave);
    };
  }, []);

  return (
    <a ref={el} className={`badge badge--${b.kind}`} href={b.href} target="_blank" rel="noreferrer" style={{ '--i': i }}>
      <span className="badge__shine" aria-hidden />
      <span className="badge__seal" aria-hidden>
        <span>{MARK[b.kind]}</span>
      </span>
      <span className="badge__issuer">{b.issuer}</span>
      <b className="badge__title">{b.title}</b>
      <span className="badge__foot">
        <span>{b.date}</span>
        <span className="badge__view">View ↗</span>
      </span>
    </a>
  );
}

export default function Badges() {
  const root = useReveal();
  const grid = useRef(null);
  useAchievementOnView(grid, 'badges', 'top 60%');

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.badge', {
        rotationY: -80,
        y: 40,
        opacity: 0,
        transformOrigin: '0% 50%',
        duration: 0.9,
        ease: 'back.out(1.4)',
        stagger: 0.08,
        scrollTrigger: { trigger: grid.current, start: 'top 80%', once: true }
      });
    }, grid);
    return () => ctx.revert();
  }, []);

  return (
    <section className="badges" id="badges" ref={root}>
      <div className="wrap">
        <div className="badges__head">
          <SectionHead
            eyebrow="Certificates · chapter 05"
            title="Badges I"
            accent="collected."
            intro="Deep learning with NVIDIA, project management with Google, and my first public role as a citizen-debate facilitator. Click any badge to see the certificate."
          />
          <div className="badges__count" data-reveal>
            <b>
              <CountUp to={badges.length} duration={1.4} />
            </b>
            <span>
              badges
              <br />
              unlocked
            </span>
          </div>
        </div>
        <div className="badges__grid" ref={grid}>
          {badges.map((b, i) => (
            <Badge b={b} i={i} key={b.title} />
          ))}
        </div>
      </div>
    </section>
  );
}
