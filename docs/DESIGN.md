# Design system — Delft Energy Twin

The website presents a research study, so it is designed like one: an editorial, report-style layout where every
colour stands for a concept from the analysis and every figure is numbered and captioned.

## 1. Design principles

| Principle | What it means on the site |
|---|---|
| **Colour carries meaning, never decoration** | One colour per concept (solar, heritage, value lost, self-consumption, change). The same colour means the same thing in text, charts, maps and the 3D view. |
| **Paper for reading, dark for instruments** | Narrative chapters sit on a warm paper background for long-form reading. The 3D twin and the building inspector are dark "instrument" surfaces, so the inferno irradiance ramp and the aerial photo keep their contrast. |
| **Read like a report** | Numbered chapters (01–08), numbered figures (*Fig. n*), captions under images, key figures set in a serif with hairline rules, limitations and data licences stated. |
| **Explain every control** | Interactive controls are numbered steps with one-line help text; every map metric has a plain-language definition shown when it is selected. |
| **Accessible by default** | WCAG AA text contrast, visible keyboard focus, 44 px touch targets on touch screens, no meaning by colour alone (labels + legends), smooth scrolling only when the user has not asked for reduced motion. |

## 2. Colour

### Neutrals (paper)

| Token | Hex | Use | Contrast on paper |
|---|---|---|---|
| `--paper` | `#F7F5F0` | page background | — |
| `--paper-2` | `#EFEBE3` | tinted bands (map explorer, method) | — |
| `--surface` | `#FFFFFF` | cards, chart panels | — |
| `--ink` | `#16191D` | headings, body text | 16.2 : 1 |
| `--ink-2` | `#454B54` | secondary text, ledes | 8.1 : 1 |
| `--ink-3` | `#646A73` | axis labels, footnotes | 5.0 : 1 |
| `--rule` | `#DAD5CB` | hairlines, grid lines | — |

### Semantic data colours

| Token | Hex | Stands for | Why this colour | Contrast on paper |
|---|---|---|---|---|
| `--delft` | `#1F3F8F` | identity, heritage, the historic centre, sequential map ramp | Delft Blue — the city's own historic colour (Delftware) | 8.9 : 1 |
| `--solar` / `--solar-ink` | `#C96A08` / `#9A4A00` | solar production (fill / text) | warm amber, the top of the irradiance ramp | 3.5 : 1 graphic / 5.8 : 1 text |
| `--home` | `#2B6F60` | power used at home (self-consumption) | calm green-teal: the value that survives 2027 | 5.4 : 1 |
| `--loss` | `#A93E2C` | value lost, exported power, not allowed, lowered | brick red, also the colour of Delft's façades | 5.7 : 1 |
| `--permit` | `#8A5D0B` | needs a permit, raised / extended | ochre: "conditional" between allowed and not allowed | 5.3 : 1 |
| `--ok` | `#37703F` | allowed, new buildings | green for "yes" | 5.4 : 1 |
| `--change` | `#5E4590` | AHN5 → AHN6 change chapter | a distinct hue that collides with none of the above | 7.1 : 1 |
| winter | `#5B78B8` | December / low sun | cool blue opposite to summer amber | 4.0 : 1 (graphic only) |

**Study areas** keep fixed colours in every chart: Binnenstad `#1F3F8F` (Delft blue), TU Delft campus `#0079A6`
(close to the university's cyan), Voorhof `#5F6F24` (olive, a green post-war district).

**Irradiance** uses the perceptually uniform *inferno* ramp (200 → 1,200 kWh/m²·yr) in the 3D tiles, the map
buildings layer and the brand mark, so the colour of a roof means the same everywhere.

**Map ramps.** Sequential metrics use a single-hue Delft-blue ramp (`#EEF1F7 → #12275A`) on a light basemap.
Diverging metrics (2027 value change) run from loss brick through warm neutral to green.

### Dark instrument surfaces

| Token | Hex | Contrast on `#14171C` |
|---|---|---|
| `--d-text` | `#ECE9E2` | 14.8 : 1 |
| `--d-muted` | `#A9AEB6` | 8.1 : 1 |
| `--d-solar` | `#F2A93B` | 9.0 : 1 |
| `--d-delft` | `#9DB4F0` | 8.7 : 1 |
| `--d-loss` | `#F0907A` | 7.7 : 1 |

## 3. Typography

| Role | Typeface | Why |
|---|---|---|
| Headings, ledes, key figures | **Newsreader** (serif, optical sizes) | designed for long-form reading; gives the report / journal register |
| Body, controls, tables | **Public Sans** | neutral, highly legible public-sector sans; tabular figures for aligned numbers |
| Labels, chapter and figure numbers, units | **IBM Plex Mono** | technical register for metadata, used sparingly at small sizes |

Body text is 16 px with 1.6 line height; ledes are 1.16 rem serif; numbers use tabular figures throughout.

## 4. Layout and components

- **Chapters**: max width 1,240 px, 88 px vertical rhythm. Each chapter has a numbered eyebrow in its chapter colour,
  a serif headline (max 22 characters per line) and a lede (max 66 characters per line).
- **Figures**: white panels with a 1 px rule and 3 px radius, no shadows or gradients. Charts and images are numbered
  automatically with CSS counters.
- **Key figures**: a row of serif numbers between a dark top rule and a hairline, separated by vertical hairlines.
- **Controls**: outlined buttons. The selected state is inverted (ink background on paper, paper background on dark
  surfaces), so it does not depend on colour alone.
- **Navigation**: a sticky top bar whose current chapter is underlined while scrolling.

## 5. Charts

Charts use ECharts with a shared theme (`web/src/charts.ts`): dotted horizontal grid lines, no vertical axis line, axis
labels in `--ink-3`, square legend keys, and white tooltips with a hairline border. The palette in `charts.ts` mirrors
the CSS tokens, so charts and text always agree.

## 6. Accessibility checklist

- [x] Text contrast ≥ 4.5 : 1 on every background (tables above)
- [x] Visible `:focus-visible` outline (2 px Delft blue)
- [x] Touch targets ≥ 44 px on coarse pointers
- [x] Selected states shown by inversion and `aria-pressed`, not colour alone
- [x] Legends and text labels next to every coloured encoding
- [x] Smooth scrolling disabled under `prefers-reduced-motion`
- [x] No horizontal page scroll at 375 px; wide tables scroll inside their own container
