import { useDeepDive } from '../components/DeepDive.jsx';
import { Chips, Pipeline, SectionHead, useReveal } from '../components/ui.jsx';
import { DelftCloud, GeoTerminal, IchkeulViz } from '../components/Visuals.jsx';
import { projects } from '../data.js';

const VIS = { ichkeul: IchkeulViz, delft: DelftCloud, georag: GeoTerminal };

function Feature({ p, flip }) {
  const { open } = useDeepDive();
  const V = VIS[p.id];
  return (
    <article className={`feature ${flip ? 'feature--flip' : ''}`} id={`p-${p.id}`}>
      <div className="feature__visual" data-reveal>
        <V />
      </div>
      <div className="feature__copy">
        <div className="feature__head" data-reveal>
          <span className="feature__num">{p.num}</span>
          <span className="eyebrow">{p.kicker}</span>
        </div>
        <h3 className="feature__title" data-reveal>
          {p.title}
        </h3>
        <p className="feature__sub serif" data-reveal>
          {p.subtitle}
        </p>
        <div className="feature__cols" data-reveal>
          <div>
            <span className="label">The challenge</span>
            <p>{p.challenge}</p>
          </div>
          <div>
            <span className="label">What I did</span>
            <p>{p.solution}</p>
          </div>
        </div>
        <div className="results" data-reveal>
          {p.results.map(r => (
            <div key={r.l}>
              <b>{r.v}</b>
              <span>{r.l}</span>
            </div>
          ))}
        </div>
        <div data-reveal>
          <Pipeline steps={p.pipeline} />
        </div>
        <div data-reveal>
          <Chips items={p.stack} />
        </div>
        <div className="row" data-reveal>
          <button className="btn btn--ink" onClick={() => open(p)}>
            Dig deeper
          </button>
          {p.deep.links.map(l => (
            <a key={l.href} className="btn btn--ghost" href={l.href} target="_blank" rel="noreferrer">
              {l.label} ↗
            </a>
          ))}
        </div>
      </div>
    </article>
  );
}

export default function Projects() {
  const root = useReveal();
  return (
    <section className="projects" id="projects" ref={root}>
      <div className="wrap">
        <SectionHead
          eyebrow="Featured projects · chapter 03"
          title="Then I zoomed out:"
          accent="orbit, cities, agents."
          intro="Three personal projects with one habit: validate against an independent reference before believing a number."
        />
        {projects.slice(1).map((p, i) => (
          <Feature p={p} key={p.id} flip={i % 2 === 1} />
        ))}
      </div>
    </section>
  );
}
