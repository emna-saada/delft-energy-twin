import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Particles from '../bits/Particles.jsx';
import CountUp from '../bits/CountUp.jsx';
import DecryptedText from '../bits/DecryptedText.jsx';
import Magnet from '../bits/Magnet.jsx';
import DetectionScene from '../components/DetectionScene.jsx';
import { useScrollTo } from '../components/Game.jsx';
import { heroStats, links } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

export default function Hero({ ready }) {
  const root = useRef(null);
  const go = useScrollTo();

  // Entrance once the loader has lifted
  useEffect(() => {
    if (!ready) return;
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'expo.out' } });
      tl.from('.hero__word span', { yPercent: 110, duration: 1.3, stagger: 0.08 })
        .from('.hero__kicker, .hero__lead, .hero__sign, .hero__actions, .hero__stats', { y: 24, opacity: 0, duration: 1, stagger: 0.08 }, '-=0.9')
        .from('.hero__sun', { scale: 0.4, opacity: 0, duration: 1.4 }, 0.1)
        .from('.hero__lens', { clipPath: 'circle(0% at 50% 50%)', duration: 1.5, ease: 'expo.inOut' }, 0.15)
        .from('.hero__badge, .hero__chip', { scale: 0, opacity: 0, duration: 0.7, ease: 'back.out(2)', stagger: 0.1 }, '-=0.6');

      // Parallax out as the next chapter comes in
      gsap.to('.hero__visual', { yPercent: -12, ease: 'none', scrollTrigger: { trigger: root.current, start: 'top top', end: 'bottom top', scrub: true } });
      gsap.to('.hero__word', { yPercent: -18, ease: 'none', stagger: 0.05, scrollTrigger: { trigger: root.current, start: 'top top', end: 'bottom top', scrub: true } });
    }, root);
    return () => ctx.revert();
  }, [ready]);

  return (
    <section className="hero" id="top" ref={root}>
      <div className="hero__mesh" aria-hidden>
        <i />
        <i />
        <i />
      </div>
      <div className="hero__particles" aria-hidden>
        <Particles particleCount={140} particleSpread={12} speed={0.06} particleColors={['#3a3fe0', '#ff4f7b', '#ffb020', '#19d3c5']} particleBaseSize={70} alphaParticles lightMode glow={0.2} moveParticlesOnHover particleHoverFactor={0.6} clickBurst={false} intro={false} />
      </div>

      <div className="hero__copy">
        <p className="hero__kicker eyebrow">Geoinformatics engineer · Computer vision for wildlife</p>
        <h1 className="hero__title" aria-label="Emna Saada">
          <span className="hero__word">
            <span>Emna</span>
          </span>
          <span className="hero__word hero__word--outline">
            <span>Saada</span>
          </span>
        </h1>
        <p className="hero__lead">
          I teach machines to <em className="serif">watch wetlands</em>: from birds in video frames to habitats seen from orbit and cities rebuilt from laser
          points. Final-year engineer at MSE, IEEE branch co-founder and trilingual translator, working with{' '}
          <DecryptedText text="rigorous, reproducible evaluation." animateOn="view" speed={35} maxIterations={14} sequential className="hl" encryptedClassName="hl hl--enc" />
        </p>
        <div className="hero__sign" aria-hidden>
          Emna <span />
        </div>
        <div className="hero__actions">
          <Magnet padding={60} magnetStrength={3}>
            <button className="btn btn--ink" onClick={() => go('#journey')}>
              ▶ Press start
            </button>
          </Magnet>
          <Magnet padding={60} magnetStrength={3}>
            <a className="btn btn--ghost" href={links.github} target="_blank" rel="noreferrer">
              GitHub ↗
            </a>
          </Magnet>
        </div>
        <dl className="hero__stats">
          {heroStats.map(s => (
            <div key={s.label}>
              <dt>
                <CountUp to={s.to} separator={s.separator || ''} duration={2.2} delay={1.6} />
                {s.suffix}
              </dt>
              <dd>{s.label}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="hero__visual">
        <div className="hero__sun" aria-hidden />
        <div className="hero__lens">
          <DetectionScene auto compact />
        </div>
        <div className="hero__badge">
          <b>ES</b>
          <span>
            Bizerte
            <br />
            Tunisia
          </span>
        </div>
        <div className="hero__chip hero__chip--a">
          <i className="dot" /> Open to a 6-month PFE · Feb 2027
        </div>
        <div className="hero__chip hero__chip--b">YOLOv9 · mAP50-95 0.626</div>
      </div>

      <button className="hero__scroll" onClick={() => go('#journey')} aria-label="Scroll to begin">
        <span>Scroll to begin the story</span>
        <i />
      </button>
    </section>
  );
}
