import { useEffect, useState } from 'react';
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import ClickSpark from './bits/ClickSpark.jsx';
import { GameProvider } from './components/Game.jsx';
import Loader from './components/Loader.jsx';
import SideRail from './components/SideRail.jsx';
import TopBar from './components/TopBar.jsx';
import DeepDive, { DeepDiveProvider } from './components/DeepDive.jsx';
import Hero from './sections/Hero.jsx';
import Journey from './sections/Journey.jsx';
import Badges from './sections/Badges.jsx';
import Cursor from './components/Cursor.jsx';
import Build from './sections/Build.jsx';
import Quest from './sections/Quest.jsx';
import Projects from './sections/Projects.jsx';
import MoreProjects from './sections/MoreProjects.jsx';
import Experience from './sections/Experience.jsx';
import Skills from './sections/Skills.jsx';
import Contact from './sections/Contact.jsx';

gsap.registerPlugin(ScrollTrigger);

export default function App() {
  const [lenis, setLenis] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const l = new Lenis({ lerp: 0.09, wheelMultiplier: 0.95, autoRaf: false });
    l.on('scroll', ScrollTrigger.update);
    const tick = t => l.raf(t * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    setLenis(l);
    return () => {
      gsap.ticker.remove(tick);
      l.destroy();
    };
  }, []);

  // Freeze scrolling while the loader plays
  useEffect(() => {
    if (!lenis) return;
    if (ready) lenis.start();
    else lenis.stop();
  }, [lenis, ready]);

  useEffect(() => {
    if (!ready) return;
    const id = setTimeout(() => ScrollTrigger.refresh(), 200);
    return () => clearTimeout(id);
  }, [ready]);

  return (
    <GameProvider lenis={lenis}>
      <DeepDiveProvider>
        <ClickSpark sparkColor="#ffb020" sparkSize={9} sparkRadius={22} sparkCount={9} duration={450}>
          <Loader onDone={() => setReady(true)} />
          <SideRail />
          <TopBar />
          <main>
            <Hero ready={ready} />
            <Journey />
            <Build />
            <Quest />
            <Projects />
            <MoreProjects />
            <Badges />
            <Experience />
            <Skills />
          </main>
          <Contact />
          <DeepDive />
          <Cursor />
        </ClickSpark>
      </DeepDiveProvider>
    </GameProvider>
  );
}
