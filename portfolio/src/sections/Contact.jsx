import { useRef, useState } from 'react';
import Magnet from '../bits/Magnet.jsx';
import ScrollVelocity from '../bits/ScrollVelocity.jsx';
import ShinyText from '../bits/ShinyText.jsx';
import { useAchievementOnView } from '../components/Game.jsx';
import { links } from '../data.js';

export default function Contact() {
  const root = useRef(null);
  const [copied, setCopied] = useState(false);
  useAchievementOnView(root, 'final', 'top 70%');

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(links.email);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.location.href = `mailto:${links.email}`;
    }
  };

  return (
    <footer className="contact dark" id="contact" ref={root}>
      <div className="contact__band" aria-hidden>
        <ScrollVelocity
          texts={['Detection · Tracking · Behaviour · ', 'Sentinel-2 · LiDAR · Grouped CV · ']}
          velocity={40}
          numCopies={6}
          className="band__text"
          outlineAlternate
          fadeEdges
        />
      </div>
      <div className="wrap contact__inner">
        <div className="contact__copy">
          <span className="eyebrow eyebrow--lagoon">Next quest · chapter 06</span>
          <h2 className="contact__title">
            Bird detection → tracking → <em className="serif">behaviour.</em>
          </h2>
          <p className="contact__lead">
            I am looking for a <b>6-month end-of-studies project (PFE) from February 2027</b> to continue this work on detection, tracking and behaviour
            recognition. Labs and teams in computer vision for ecology or Earth observation: let’s talk.
          </p>
          <div className="contact__mail">
            <a href={`mailto:${links.email}`}>
              <ShinyText text={links.email} color="#cfe9e2" shineColor="#ffffff" speed={3} />
            </a>
            <button className="btn btn--small btn--ghost-dark" onClick={copy}>
              {copied ? 'Copied ✓' : 'Copy'}
            </button>
          </div>
          <div className="row">
            <Magnet padding={50} magnetStrength={3}>
              <a className="btn btn--lagoon" href={`mailto:${links.email}?subject=PFE%202027`}>
                Send a message
              </a>
            </Magnet>
            <Magnet padding={50} magnetStrength={3}>
              <a className="btn btn--ghost-dark" href={links.linkedin} target="_blank" rel="noreferrer">
                LinkedIn ↗
              </a>
            </Magnet>
            <Magnet padding={50} magnetStrength={3}>
              <a className="btn btn--ghost-dark" href={links.github} target="_blank" rel="noreferrer">
                GitHub ↗
              </a>
            </Magnet>
            {links.cv && (
              <Magnet padding={50} magnetStrength={3}>
                <a className="btn btn--ghost-dark" href={links.cv} target="_blank" rel="noreferrer">
                  CV (PDF) ↓
                </a>
              </Magnet>
            )}
          </div>
        </div>
        <div className="contact__script" aria-hidden>
          <span>Let’s fly</span>
          <svg viewBox="0 0 120 60" className="contact__bird">
            <path d="M60 30 Q40 6 8 18 Q36 20 60 40 Q84 20 112 18 Q80 6 60 30Z" fill="currentColor" />
          </svg>
        </div>
      </div>
      <div className="wrap contact__foot">
        <span>© 2026 Emna Saada</span>
        <span>Geoinformatics · Computer vision · Earth observation · Bizerte, Tunisia</span>
        <span>Built with React, GSAP, Lenis & React Bits</span>
      </div>
    </footer>
  );
}
