// Render docs/linkedin/slides.html to 1080x1350 PNG slides and a PDF carousel.
const { chromium } = require('playwright');
const path = require('path');
const dir = path.join(__dirname, '..', 'docs', 'linkedin');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.join(dir, 'slides.html'));
  await p.waitForTimeout(500);
  const n = await p.locator('section.slide').count();
  for (let i = 0; i < n; i++) await p.locator('section.slide').nth(i).screenshot({ path: path.join(dir, `slide_${i + 1}.png`) });
  await p.addStyleTag({ content: 'body{background:#fff} .slide{margin:0;break-after:page}' });
  await p.pdf({ path: path.join(dir, 'ClimaRisk_Tunisie_carousel.pdf'), width: '1080px', height: '1350px', printBackground: true });
  await b.close();
  console.log(n, 'slides');
})();
