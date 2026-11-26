import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

/** Desktop-only cursor: a dot plus a lagging ring that grows over interactive elements. */
export default function Cursor() {
  const dot = useRef(null);
  const ring = useRef(null);
  useEffect(() => {
    if (!window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)').matches) return;
    document.documentElement.classList.add('has-cursor');
    const dx = gsap.quickTo(dot.current, 'x', { duration: 0.08 });
    const dy = gsap.quickTo(dot.current, 'y', { duration: 0.08 });
    const rx = gsap.quickTo(ring.current, 'x', { duration: 0.45, ease: 'power3' });
    const ry = gsap.quickTo(ring.current, 'y', { duration: 0.45, ease: 'power3' });
    const move = e => {
      dx(e.clientX);
      dy(e.clientY);
      rx(e.clientX);
      ry(e.clientY);
      const hot = e.target.closest?.('a, button, input, .badge, .stop__card');
      ring.current.classList.toggle('is-hot', !!hot);
    };
    window.addEventListener('pointermove', move);
    return () => {
      window.removeEventListener('pointermove', move);
      document.documentElement.classList.remove('has-cursor');
    };
  }, []);
  return (
    <>
      <span className="cursor-dot" ref={dot} aria-hidden />
      <span className="cursor-ring" ref={ring} aria-hidden />
    </>
  );
}
