// Records a walkthrough of the local Streamlit dashboard (make app must be running on :8501).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, '..', 'public', 'capture');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } } });
  const p = await ctx.newPage();
  await p.goto('http://localhost:8501', { waitUntil: 'networkidle' });
  await p.waitForSelector('text=EAD totale', { timeout: 60000 });
  await p.waitForTimeout(2500);
  await p.getByText('SSP5-8.5', { exact: true }).first().click();       // scenario filter
  await p.waitForTimeout(3500);
  await p.mouse.wheel(0, 500); await p.waitForTimeout(2500); await p.mouse.wheel(0, -500);
  await p.getByRole('tab', { name: 'Carte' }).click();                   // map
  await p.waitForTimeout(4500);
  await p.getByText('Sécheresse', { exact: true }).first().click();
  await p.waitForTimeout(3500);
  await p.getByRole('tab', { name: 'Analyse' }).click();                 // heatmap
  await p.waitForTimeout(3500);
  await p.mouse.wheel(0, 700); await p.waitForTimeout(2500);
  await p.mouse.wheel(0, -700);
  await p.getByRole('tab', { name: 'Fiche crédit' }).click();            // credit sheet
  await p.waitForTimeout(4000);
  await p.getByRole('tab', { name: 'Reporting' }).click();               // export
  await p.waitForTimeout(3000);
  await p.getByRole('button', { name: /Rapport PDF|Exporter les crédits/ }).first().hover();
  await p.waitForTimeout(2500);
  const v = p.video();
  await ctx.close(); await b.close();
  fs.renameSync(await v.path(), path.join(OUT, 'dashboard.webm'));
})();
