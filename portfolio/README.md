# Emna Saada · portfolio

A story-driven, game-like portfolio: React + Vite, **GSAP** (ScrollTrigger, Flip, SplitText),
**Lenis** smooth scrolling and components from **React Bits** (SplitText, CountUp, DecryptedText,
ShinyText, ScrollVelocity, SpotlightCard, Magnet, ClickSpark, Particles — MIT + Commons Clause, see reactbits.dev).

## Chapters

0. Boot screen + hero (live "detector lens")
1. What I build — pinned card deck (computer vision, Earth observation, LiDAR, AI agents)
2. Main quest — Visual WetlandBirds internship: detector demo, metrics vs paper, the data-leak "boss fight", classification
3. Featured projects — Ichkeul time slider, Delft point cloud assembling on scroll, GeoRAG agent terminal
4. Side quests (filterable), experience timeline, skills, method wheel, education, trophies
5. Next quest — PFE February 2027, contact

Every project has a **Dig deeper** drawer: how it works, code & demos, and references.
Achievements unlock as you scroll; the left rail shows XP (scroll progress).

Content lives in `src/data.js` (from the CV). Illustrations are schematic and labelled as such.

## Run

```bash
npm install
npm run dev
```

## Deploy

`npm run build` writes a static site to `dist/` (relative paths, works anywhere).

- **Vercel / Netlify:** import the repo, set the root directory to `portfolio`, build `npm run build`, output `dist`.
- **GitHub Pages:** create a repo named `emna-saada.github.io`, copy this folder into it, and deploy `dist/` with the Pages action.
