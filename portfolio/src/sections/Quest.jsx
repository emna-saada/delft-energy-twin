import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import CountUp from '../bits/CountUp.jsx';
import SpotlightCard from '../bits/SpotlightCard.jsx';
import DetectionScene from '../components/DetectionScene.jsx';
import LeakageGame from '../components/LeakageGame.jsx';
import { useAchievementOnView, useGame } from '../components/Game.jsx';
import { useDeepDive } from '../components/DeepDive.jsx';
import { Chips, Pipeline, SectionHead, useReveal } from '../components/ui.jsx';
import { projects, wetland } from '../data.js';

gsap.registerPlugin(ScrollTrigger);

const project = projects[0];

function Level({ n, title, children, aside }) {
  return (
    <div className="level" data-reveal>
      <div className="level__tag">
        <span>Level {n}</span>
        <b>{title}</b>
      </div>
      {aside}
      {children}
    </div>
  );
}

function MetricsDuel() {
  const ref = useRef(null);
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.duel__bar i', {
        scaleX: 0,
        transformOrigin: 'left center',
        duration: 1.3,
        ease: 'expo.out',
        stagger: 0.08,
        scrollTrigger: { trigger: ref.current, start: 'top 75%', once: true }
      });
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div className="duel" ref={ref}>
      <div className="duel__legend">
        <span>
          <i className="sw sw--paper" /> Paper (2025)
        </span>
        <span>
          <i className="sw sw--ours" /> Ours · YOLOv9
        </span>
      </div>
      {wetland.metrics.map(m => (
        <div className="duel__row" key={m.name}>
          <span className="duel__name">{m.name}</span>
          <div className="duel__bars">
            <div className="duel__bar duel__bar--paper">
              <i style={{ width: `${m.paper * 100}%` }} />
              <b>{m.paper.toFixed(3)}</b>
            </div>
            <div className="duel__bar duel__bar--ours">
              <i style={{ width: `${m.ours * 100}%` }} />
              <b>
                <CountUp to={m.ours} decimals={3} duration={1.6} />
              </b>
            </div>
          </div>
          <span className="duel__gain">+{(((m.ours - m.paper) / m.paper) * 100).toFixed(1)}%</span>
        </div>
      ))}
      <p className="fine">First completed tuning fold, preliminary (about 31 h per fold on an RTX 4060 laptop GPU). Multi-seed evaluation on the official test videos is next.</p>
    </div>
  );
}

function ClassBars() {
  const ref = useRef(null);
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.cbar__fill', {
        scaleX: 0,
        transformOrigin: 'left center',
        duration: 1.4,
        ease: 'expo.out',
        stagger: 0.12,
        scrollTrigger: { trigger: ref.current, start: 'top 78%', once: true }
      });
    }, ref);
    return () => ctx.revert();
  }, []);
  return (
    <div className="cbars" ref={ref}>
      {wetland.classification.map(c => (
        <div className={`cbar cbar--${c.tone}`} key={c.label}>
          <div className="cbar__label">
            <span>{c.label}</span>
            <b>{c.from ? c.note : `${c.value}%`}</b>
          </div>
          <div className="cbar__track">
            <span className="cbar__fill" style={{ left: c.from ? `${c.from}%` : 0, width: `${c.from ? c.value - c.from : c.value}%` }} />
          </div>
          {!c.from && <small>{c.note}</small>}
        </div>
      ))}
    </div>
  );
}

export default function Quest() {
  const root = useReveal();
  const detRef = useRef(null);
  const [running, setRunning] = useState(false);
  const { open } = useDeepDive();
  const { unlock } = useGame();
  useAchievementOnView(detRef, 'baseline', 'top 40%');

  const run = () => {
    setRunning(false);
    requestAnimationFrame(() => setRunning(true));
  };

  return (
    <section className="quest dark" id="quest" ref={root}>
      <div className="quest__glow" aria-hidden />
      <div className="wrap">
        <SectionHead
          dark
          eyebrow="Main quest · chapter 02 · Jul – Aug 2026"
          title="Can a detector beat a Nature benchmark,"
          accent="honestly?"
          intro="My summer research internship at MSE with the Efrei Research Lab. The mission: reproduce, then improve, the baselines of Visual WetlandBirds (Scientific Data, 2025), in a team of two."
        />

        <div className="quest__brief" data-reveal>
          {wetland.setting.map(s => (
            <div key={s.label}>
              <b>
                <CountUp to={s.to} duration={1.8} />
              </b>
              <span>{s.label}</span>
            </div>
          ))}
          <div className="quest__beh">
            <span className="eyebrow">7 behaviours to recognise</span>
            <Chips items={wetland.behaviours} dark />
          </div>
        </div>

        <Level n="1" title="Detect every bird">
          <div className="quest__det" ref={detRef}>
            <div className="quest__scene">
              <DetectionScene running={running} />
              <button className="btn btn--lagoon quest__run" onClick={run}>
                {running ? '↻ Run again' : '▶ Run YOLOv9'}
              </button>
              <span className="quest__caption">Illustration of a detector pass, not a dataset frame</span>
            </div>
            <div>
              <h3 className="h3">
                YOLOv9 beat the published baseline on <em className="serif">all four</em> metrics
              </h3>
              <p className="muted">yolov9c, COCO-pretrained, trained with the paper’s frame sampling.</p>
              <MetricsDuel />
            </div>
          </div>
        </Level>

        <Level n="2" title="Boss fight: my own data leak">
          <div className="quest__boss">
            <div>
              <h3 className="h3">
                The numbers looked great. <em className="serif">Too great.</em>
              </h3>
              <p className="muted">
                I first compared 4 CNNs with stratified 5-fold cross-validation. Auditing my own pipeline, I found crop-level leakage: frames from the same video
                were landing in both train and test. Try it: switch the split and watch the leaks disappear.
              </p>
              <ol className="protocol">
                {wetland.protocol.map((p, i) => (
                  <li key={p.t}>
                    <span>{String(i + 1).padStart(2, '0')}</span>
                    <div>
                      <b>{p.t}</b>
                      <p>{p.d}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <LeakageGame />
          </div>
        </Level>

        <Level n="3" title="Who is it, and what is it doing?">
          <div className="quest__cls">
            <div>
              <h3 className="h3">
                Species: nearly solved. Behaviour: <em className="serif">the next frontier.</em>
              </h3>
              <p className="muted">
                Species recognition reaches 96.95% with frozen EfficientNet-B0 embeddings and logistic regression. Behaviour, from 4 pooled frames, beats the S3D
                baseline but not the paper’s video models.
              </p>
              <div className="insight">
                <span className="eyebrow">What this tells us</span>
                <p>
                  Behaviour needs <b>time</b>: temporal models and <b>tracking</b>. That is exactly what I want to build in my PFE.
                </p>
              </div>
            </div>
            <ClassBars />
          </div>
        </Level>

        <div className="quest__loot" data-reveal>
          <SpotlightCard className="loot" spotlightColor="rgba(87, 214, 191, 0.22)" theme="deep">
            <span className="eyebrow">Engineering loot</span>
            <ul>
              {wetland.engineering.map(e => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </SpotlightCard>
          <div className="quest__cta">
            <Pipeline steps={project.pipeline} dark />
            <p className="muted small">{project.team}</p>
            <div className="row">
              <button className="btn btn--lagoon" onClick={() => open(project)}>
                Dig deeper: method, code, references
              </button>
              <a className="btn btn--ghost-dark" href={project.deep.links[0].href} target="_blank" rel="noreferrer" onClick={() => unlock('curious')}>
                Code on GitHub ↗
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
