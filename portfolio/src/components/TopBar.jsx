import { useEffect, useState } from 'react';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { links, nav } from '../data.js';
import { useScrollTo } from './Game.jsx';

export default function TopBar() {
  const [active, setActive] = useState('');
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const go = useScrollTo();

  useEffect(() => {
    const triggers = nav.map(({ id }) =>
      ScrollTrigger.create({
        trigger: `#${id}`,
        start: 'top 45%',
        end: 'bottom 45%',
        onToggle: self => self.isActive && setActive(id)
      })
    );
    const top = ScrollTrigger.create({ start: 80, end: 'max', onToggle: self => setScrolled(self.isActive) });
    return () => [...triggers, top].forEach(t => t.kill());
  }, []);

  const click = id => e => {
    e.preventDefault();
    setOpen(false);
    go(`#${id}`);
  };

  return (
    <header className={`topbar ${scrolled ? 'is-scrolled' : ''} ${open ? 'is-open' : ''}`}>
      <a href="#top" className="topbar__name" onClick={click('top')}>
        Emna Saada
      </a>
      <nav className="topbar__nav" aria-label="Sections">
        {nav.map(({ id, label }) => (
          <a key={id} href={`#${id}`} className={active === id ? 'is-active' : ''} onClick={click(id)}>
            {label}
          </a>
        ))}
      </nav>
      {links.cv && (
        <a className="btn btn--small btn--ink topbar__cv" href={links.cv} target="_blank" rel="noreferrer">
          CV ↓
        </a>
      )}
      <button className="topbar__burger" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>
        <span />
        <span />
      </button>
    </header>
  );
}
