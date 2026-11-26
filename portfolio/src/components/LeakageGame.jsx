import { useLayoutEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { Flip } from 'gsap/Flip';
import { useGame } from './Game.jsx';

gsap.registerPlugin(Flip);

const VIDEOS = ['A', 'B', 'C', 'D'];
const FRAMES = 6;
// "Random frame split": a few frames of every video end up in test.
const RANDOM_TEST = new Set(['A1', 'A4', 'B2', 'C0', 'C5', 'D3']);
const frames = VIDEOS.flatMap(v => Array.from({ length: FRAMES }, (_, i) => `${v}${i}`));

/**
 * Interactive explanation of the leakage Emna found in her own pipeline:
 * frames from the same video on both sides of the split inflate the score.
 */
export default function LeakageGame() {
  const [mode, setMode] = useState('random');
  const flipState = useRef(null);
  const root = useRef(null);
  const { unlock } = useGame();

  const inTest = id => (mode === 'random' ? RANDOM_TEST.has(id) : id[0] === 'D');
  const test = frames.filter(inTest);
  const train = frames.filter(f => !inTest(f));
  const trainVideos = new Set(train.map(f => f[0]));
  const leaks = test.filter(f => trainVideos.has(f[0])).length;

  const switchTo = m => {
    if (m === mode) return;
    flipState.current = Flip.getState(root.current.querySelectorAll('.frame'));
    setMode(m);
    if (m === 'grouped') setTimeout(() => unlock('leak'), 900);
  };

  useLayoutEffect(() => {
    if (!flipState.current) return;
    Flip.from(flipState.current, { duration: 0.9, ease: 'power3.inOut', stagger: 0.015, absolute: true });
    flipState.current = null;
  }, [mode]);

  const Frame = ({ id }) => {
    const leak = mode === 'random' && inTest(id) && trainVideos.has(id[0]);
    const twin = mode === 'random' && !inTest(id) && test.some(t => t[0] === id[0]);
    return (
      <span className={`frame frame--${id[0]} ${leak ? 'is-leak' : ''} ${twin ? 'is-twin' : ''}`} data-flip-id={id}>
        {id[0]}
        <sub>{id[1]}</sub>
      </span>
    );
  };

  return (
    <div className="leak" ref={root}>
      <div className="leak__controls" role="radiogroup" aria-label="Split strategy">
        <button role="radio" aria-checked={mode === 'random'} className={mode === 'random' ? 'is-on' : ''} onClick={() => switchTo('random')}>
          Random frame split
        </button>
        <button role="radio" aria-checked={mode === 'grouped'} className={mode === 'grouped' ? 'is-on' : ''} onClick={() => switchTo('grouped')}>
          Video-grouped split
        </button>
      </div>

      <div className="leak__board">
        <div className="leak__bin">
          <h4>
            Train <small>{train.length} frames</small>
          </h4>
          <div className="leak__cells">
            {train.map(id => (
              <Frame id={id} key={id} />
            ))}
          </div>
        </div>
        <div className={`leak__bin leak__bin--test ${mode === 'grouped' ? 'is-locked' : ''}`}>
          <h4>
            Test <small>{test.length} frames</small>
            {mode === 'grouped' && (
              <span className="lock" aria-label="locked">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <rect x="5" y="11" width="14" height="10" rx="2" />
                  <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                </svg>
                locked
              </span>
            )}
          </h4>
          <div className="leak__cells">
            {test.map(id => (
              <Frame id={id} key={id} />
            ))}
          </div>
        </div>
      </div>

      <div className={`leak__meter ${leaks ? 'is-bad' : 'is-good'}`}>
        <b>
          {leaks}/{test.length}
        </b>
        <span>
          {leaks
            ? 'test frames have a near-identical sibling in train: the model is graded on scenes it has already seen, so the score looks better than it is.'
            : 'leaks: every test video is unseen during training. The score now measures generalisation to new footage.'}
        </span>
      </div>
      <pre className="leak__code">
        <span className="c-dim"># the idea behind the locked fold</span>
        {'\n'}assert set(test_videos).isdisjoint(train_videos)
      </pre>
    </div>
  );
}
