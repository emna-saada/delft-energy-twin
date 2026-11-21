# Demo video (Remotion)

- `npm run props` — reads `../outputs/kpis.json`, writes `public/props.json`, generates the French voice-over with Piper TTS (voice `fr_FR-siwis-medium`, dataset CC BY 4.0, download into `voice_model/`) and `out/climarisk_demo.srt`.
- `npm run capture` — Playwright records the local dashboard (`make app` must be running).
- `npm run render` — 1920×1080 H.264 MP4, 30 fps, ~3 min, one composition per storyboard scene (`src/scenes/`).

No music, no third-party logos (organisations are named in text only). Remotion is free for individuals (licence FAQ checked 2026-11-20).
