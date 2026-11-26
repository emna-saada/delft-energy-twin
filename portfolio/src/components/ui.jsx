import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import SplitText from '../bits/SplitText.jsx';

gsap.registerPlugin(ScrollTrigger);

/** Fades up every [data-reveal] child of the returned ref as it enters the viewport. */
export function useReveal() {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const ctx = gsap.context(() => {
      const items = gsap.utils.toArray('[data-reveal]');
      gsap.set(items, { y: 36, opacity: 0 });
      ScrollTrigger.batch(items, {
        start: 'top 88%',
        once: true,
        onEnter: batch => gsap.to(batch, { y: 0, opacity: 1, duration: 0.9, ease: 'power3.out', stagger: 0.09, overwrite: true })
      });
    }, ref);
    return () => ctx.revert();
  }, []);
  return ref;
}

export function SectionHead({ eyebrow, title, accent, intro, dark = false, align = 'left' }) {
  return (
    <div className={`shead shead--${align} ${dark ? 'shead--dark' : ''}`}>
      <div className="shead__eyebrow" data-reveal>
        <span>{eyebrow}</span>
        <i />
      </div>
      <h2 className="shead__title">
        <SplitText text={title} tag="span" splitType="words" effect="rise" mask delay={70} textAlign={align} className="shead__split" />
        {accent && (
          <>
            {' '}
            <em className="serif">{accent}</em>
          </>
        )}
      </h2>
      {intro && (
        <p className="shead__intro" data-reveal>
          {intro}
        </p>
      )}
    </div>
  );
}

export function Chips({ items, dark }) {
  return (
    <div className="chips">
      {items.map(s => (
        <span className={`chip ${dark ? 'chip--dark' : ''}`} key={s}>
          {s}
        </span>
      ))}
    </div>
  );
}

export function Pipeline({ steps, dark }) {
  return (
    <div className={`pipeline ${dark ? 'pipeline--dark' : ''}`}>
      {steps.map((s, i) => (
        <span key={s} className="pipeline__step">
          <code>{s}</code>
          {i < steps.length - 1 && <i aria-hidden>→</i>}
        </span>
      ))}
    </div>
  );
}

export function Arrow() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}
