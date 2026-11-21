# LinkedIn post: draft for Emna to review and publish

**Format:** document post. Upload `ClimaRisk_Tunisie_carousel.pdf` (7 pages, 1080×1350), or the seven `slide_*.png` files as an image post. Put the GitHub link in the first comment, once the repository is public, rather than in the post body.

**Before posting:** check every figure against `outputs/kpis.json`, make sure the repository is public, keep the word "synthétique" in the post, and be ready to explain every step in your own words (method, PD/EL logic, NGFS limits). If you mention how the project was built, say so plainly.

---

## Version française (recommandée)

Quand le climat change, le risque de crédit change aussi. 🌡️

Je partage ClimaRisk Tunisie, un outil open source qui relie chaque crédit d'un portefeuille bancaire à son exposition aux risques climatiques physiques : chaleur extrême, sécheresse, inondation et feux de forêt.

L'idée : transformer des pixels satellites et climatiques en indicateurs qu'une direction des risques peut lire.

Ce que fait l'outil :
→ géolocalise 2 000 crédits répartis sur les 24 gouvernorats ;
→ mesure les aléas aujourd'hui, en 2030 et en 2050, avec 5 modèles climatiques CMIP6 (NASA), les cartes d'inondation WRI Aqueduct et l'occupation du sol ESA WorldCover ;
→ traduit l'exposition en ajustement de la probabilité de défaut et de la perte attendue, par secteur et par gouvernorat ;
→ produit un tableau de bord, un rapport méthodologique et une vidéo de démonstration.

Ce que montrent les résultats (scénario SSP5-8.5, horizon 2050) :
• la part de l'encours en zone d'aléa élevé passe de 1,5 % à 22,4 % ;
• la perte attendue augmente de 4,8 M TND par rapport au climat actuel ;
• la céréaliculture et l'oléiculture sont les plus touchées, avec El Kef, Siliana et Zaghouan en tête.

Trois enseignements :
1️⃣ L'hypothèse de crédit (l'élasticité de la PD) pèse bien plus que l'incertitude climatique : c'est elle qu'il faut calibrer en priorité.
2️⃣ Deux indicateurs de sécheresse peuvent désigner des régions opposées. Le bon choix dépend de l'activité financée.
3️⃣ La fonction de dommage PIB des scénarios NGFS Phase V repose sur un article rétracté. J'ai préféré ne pas l'utiliser.

⚠️ Important : le portefeuille est 100 % synthétique (aucune donnée client, loi organique 2004-63). Les montants illustrent la méthode et ne décrivent aucune banque tunisienne.

Le projet s'inscrit dans la dynamique de la feuille de route 2026-2030 de la BCT sur la finance verte et les risques climatiques, et dans les cadres BCBS, NGFS, EBA et IFRS S2.

Code, rapport et vidéo : lien en commentaire. Les retours de professionnels du risque et de la finance durable sont les bienvenus.

#Géoinformatique #RisqueClimatique #RisqueDeCrédit #FinanceDurable #Tunisie #DataScience #NGFS

---

## English version

When the climate changes, credit risk changes too. 🌡️

I built ClimaRisk Tunisie, an open-source tool that links every loan in a bank portfolio to its exposure to physical climate hazards: extreme heat, drought, flooding and wildfire.

The goal is to turn satellite and climate pixels into indicators a risk committee can read.

What it does:
→ geolocates 2,000 loans across Tunisia's 24 governorates;
→ measures hazards today, in 2030 and in 2050, using 5 CMIP6 climate models (NASA), WRI Aqueduct flood maps and ESA WorldCover land cover;
→ translates exposure into adjusted probability of default and expected loss, by sector and governorate;
→ ships a dashboard, a methodology report and a demo video.

What the results show (SSP5-8.5, 2050):
• the share of the loan book in a high-hazard zone rises from 1.5 % to 22.4 %;
• expected loss rises by TND 4.8 M compared with today's climate;
• cereal and olive farming are hit hardest, led by El Kef, Siliana and Zaghouan.

Three lessons:
1️⃣ The credit assumption (PD elasticity) matters far more than climate-model uncertainty, so it is the first thing to calibrate.
2️⃣ Two drought indicators can point to opposite regions. The right one depends on what is being financed.
3️⃣ The GDP-damage function in NGFS Phase V relies on a retracted paper, so I left it out.

⚠️ The portfolio is 100 % synthetic, with no client data. The figures illustrate the method and describe no real bank.

Code, report and video in the first comment. Feedback from risk and sustainable-finance professionals is very welcome.

#Geoinformatics #ClimateRisk #CreditRisk #SustainableFinance #Tunisia #DataScience

---

## First comment (once the repository is public)

📂 Code (MIT): https://github.com/emna-saada/climarisk-tunisia
📄 Methodology report (PDF, FR): in `docs/report.pdf`
🎬 3-minute demo video: in `video/out/climarisk_demo.mp4`

## Alt text for the slides (paste into LinkedIn's alt-text field)

1. Three maps of Tunisia showing 2,000 synthetic loans coloured by climate hazard score today, under SSP2-4.5 in 2050 and under SSP5-8.5 in 2050; scores rise across the north and centre.
2. Four-step method: synthetic portfolio, hazard measurement, sector vulnerability, credit translation into PD and expected loss.
3. Key result: the share of the loan book in a high-hazard zone rises from 1.5 % today to 22.4 % in 2050 under SSP5-8.5; expected loss rises by 4.8 million TND versus today.
4. Two maps of days above 35 °C per year, 2010–2014 versus SSP5-8.5 in 2050; the hot zone spreads from the south to the centre.
5. Extra expected loss by sector, led by cereals (84 bp) and olives (71 bp), with a sector-by-hazard heatmap.
6. Screenshots of the results dashboard and the demo video.
7. Lessons learned and limits, with the project's tools: Python, CMIP6, NGFS, geoinformatics, credit risk.
