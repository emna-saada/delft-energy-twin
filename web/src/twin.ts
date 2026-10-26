// CesiumJS 3D twin: self-hosted 3D Tiles (no Cesium ion), sun & shadow control, picking -> inspector.
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import { AOI_LABEL, AOIS, AoiKey, dataUrl, load, onState } from "./data";
import { buildingAt, buildings, renderInspector, searchAddress } from "./inspector";

declare const CESIUM_BASE_URL: string;
(window as any).CESIUM_BASE_URL = CESIUM_BASE_URL;

/** Local Amsterdam wall-clock time -> JS Date (UTC), handling daylight saving via Intl. */
function amsterdam(y: number, m: number, d: number, hour: number): Date {
  const guess = new Date(Date.UTC(y, m, d, Math.floor(hour), Math.round((hour % 1) * 60)) - 3600e3);
  const parts = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Amsterdam", hour: "2-digit", hourCycle: "h23" })
    .formatToParts(guess);
  const shown = +parts.find((p) => p.type === "hour")!.value;
  return new Date(guess.getTime() + (Math.floor(hour) - shown) * 3600e3);
}

export interface Twin { viewer: Cesium.Viewer; flyTo: (a: AoiKey) => void; select: (lon: number, lat: number) => Promise<void> }

export async function initTwin(container: HTMLElement, panel: HTMLElement, inspector: HTMLElement): Promise<Twin> {
  // PDOK aerial photo (open, no key), dimmed so the solar colours stay readable
  const aerial = new Cesium.ImageryLayer(new Cesium.UrlTemplateImageryProvider({
    url: "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
    maximumLevel: 19, credit: new Cesium.Credit("Luchtfoto © Beeldmateriaal Nederland / PDOK (CC BY 4.0)"),
  }), { brightness: 0.55, saturation: 0.55, contrast: 1.05 });
  const viewer = new Cesium.Viewer(container, {
    baseLayer: aerial,
    baseLayerPicker: false, geocoder: false, homeButton: false, sceneModePicker: false, navigationHelpButton: false,
    animation: false, timeline: false, fullscreenButton: false, infoBox: false, selectionIndicator: false,
    shadows: true, requestRenderMode: true, maximumRenderTimeChange: Infinity,
  });
  const scene = viewer.scene;
  scene.globe.baseColor = Cesium.Color.fromCssColorString("#0e1014");
  scene.backgroundColor = Cesium.Color.fromCssColorString("#0e1014");
  scene.globe.depthTestAgainstTerrain = false;
  viewer.shadowMap.softShadows = true;
  viewer.shadowMap.darkness = 0.35;
  viewer.shadowMap.maximumDistance = 2500;
  scene.postProcessStages.fxaa.enabled = true;

  const tileset = await Cesium.Cesium3DTileset.fromUrl(dataUrl("tileset.json"), {
    maximumScreenSpaceError: 6, shadows: Cesium.ShadowMode.ENABLED,
  });
  scene.primitives.add(tileset);
  // requestRenderMode stops drawing when the camera stops; keep rendering until imagery and tiles have refined
  scene.postRender.addEventListener(() => {
    if (!scene.globe.tilesLoaded || !tileset.tilesLoaded) scene.requestRender();
  });

  // ---------------- district views from the buurten (AOI bounding boxes)
  const buurten = await load<any>("buurten.geojson");
  const views = {} as Record<AoiKey, Cesium.Rectangle>;
  for (const a of AOIS) {
    const xs: number[] = [], ys: number[] = [];
    for (const f of buurten.features.filter((f: any) => f.properties.aoi === a)) {
      const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
      for (const p of polys) for (const [x, y] of p[0]) { xs.push(x); ys.push(y); }
    }
    views[a] = Cesium.Rectangle.fromDegrees(Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys));
  }
  const flyTo = (a: AoiKey) => {
    const c = Cesium.Rectangle.center(views[a]);
    const lat = Cesium.Math.toDegrees(c.latitude), lon = Cesium.Math.toDegrees(c.longitude);
    viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(lon, lat - 0.0105, 820),
      orientation: { heading: 0, pitch: Cesium.Math.toRadians(-38), roll: 0 }, duration: 1.6 });
  };

  // ---------------- controls
  panel.insertAdjacentHTML("beforeend", `
    <div class="ctl"><div class="ctl-title"><span class="step">2</span> Fly to a district</div>
      <p class="hint">Historic centre, university campus, or post-war Voorhof.</p>
      <div class="btn-row">${AOIS.map((a) => `<button data-aoi="${a}">${AOI_LABEL[a]}</button>`).join("")}</div></div>
    <div class="ctl"><div class="ctl-title"><span class="step">3</span> Find an address</div>
      <p class="hint">Any address in Delft (PDOK address register); the building opens in the inspector.</p>
      <input type="search" id="addr" placeholder="e.g. Markt 87" autocomplete="off" aria-label="Address in Delft" />
      <ul class="results" id="addr-results"></ul></div>
    <div class="ctl"><div class="ctl-title"><span class="step">4</span> Move the sun</div>
      <p class="hint">Real shadows for that moment. Try 21 Dec at 10:00: the low winter sun leaves whole streets in shade.</p>
      <div class="time-row">
        <select id="sun-date" aria-label="Date">
          <option value="2,21">21 Mar</option><option value="5,21" selected>21 Jun</option>
          <option value="8,21">21 Sep</option><option value="11,21">21 Dec</option>
        </select>
        <input type="range" id="sun-hour" min="6" max="21" step="0.25" value="13" aria-label="Hour of day" />
        <span class="time-label" id="sun-label">13:00</span>
      </div>
      <label class="check"><input type="checkbox" id="shadows" checked /> Cast shadows</label>
    </div>`);
  panel.querySelectorAll<HTMLButtonElement>("[data-aoi]").forEach((b) => b.addEventListener("click", () => flyTo(b.dataset.aoi as AoiKey)));

  const date = panel.querySelector<HTMLSelectElement>("#sun-date")!;
  const hour = panel.querySelector<HTMLInputElement>("#sun-hour")!;
  const label = panel.querySelector<HTMLElement>("#sun-label")!;
  const setSun = () => {
    const [m, d] = date.value.split(",").map(Number);
    const h = +hour.value;
    label.textContent = `${String(Math.floor(h)).padStart(2, "0")}:${String(Math.round((h % 1) * 60)).padStart(2, "0")}`;
    viewer.clock.currentTime = Cesium.JulianDate.fromDate(amsterdam(2026, m, d, h));
    scene.requestRender();
  };
  date.addEventListener("change", setSun);
  hour.addEventListener("input", setSun);
  panel.querySelector<HTMLInputElement>("#shadows")!.addEventListener("change", (e) => {
    viewer.shadows = (e.target as HTMLInputElement).checked;
    scene.requestRender();
  });
  setSun();

  // ---------------- picking -> inspector
  const highlight = viewer.entities.add({ show: false });
  let selected: string | null = null;
  const close = () => { inspector.hidden = true; highlight.show = false; selected = null; scene.requestRender(); };
  const select = async (lon: number, lat: number) => {
    const fp = await buildingAt(lon, lat);
    if (!fp) { close(); return; }
    const b = (await buildings())[fp.id];
    selected = fp.id;
    renderInspector(inspector, fp.id, b, close);
    highlight.polygon = new Cesium.PolygonGraphics({
      hierarchy: new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(fp.rings[0].flat()),
        fp.rings.slice(1).map((h) => new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(h.flat())))),
      height: 0, extrudedHeight: (b?.h ?? 10) + 0.6,
      material: Cesium.Color.fromCssColorString("#4fd1c5").withAlpha(0.35),
      outline: true, outlineColor: Cesium.Color.fromCssColorString("#4fd1c5"),
    });
    highlight.show = true;
    scene.requestRender();
  };
  new Cesium.ScreenSpaceEventHandler(scene.canvas).setInputAction(async (e: any) => {
    const p = scene.pickPositionSupported ? scene.pickPosition(e.position) : undefined;
    const cart = p ? Cesium.Cartographic.fromCartesian(p) : viewer.camera.pickEllipsoid(e.position) &&
      Cesium.Cartographic.fromCartesian(viewer.camera.pickEllipsoid(e.position)!);
    if (!cart) return;
    await select(Cesium.Math.toDegrees(cart.longitude), Cesium.Math.toDegrees(cart.latitude));
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  onState(async () => { if (selected) renderInspector(inspector, selected, (await buildings())[selected], close); });

  // ---------------- address search
  const addr = panel.querySelector<HTMLInputElement>("#addr")!;
  const results = panel.querySelector<HTMLUListElement>("#addr-results")!;
  let t: number | undefined;
  addr.addEventListener("input", () => {
    clearTimeout(t);
    t = window.setTimeout(async () => {
      const q = addr.value.trim();
      if (q.length < 3) { results.innerHTML = ""; return; }
      const hits = await searchAddress(q);
      results.innerHTML = hits.map((h, i) => `<li><button data-i="${i}">${h.label}</button></li>`).join("") ||
        `<li class="muted small">No address found in Delft.</li>`;
      results.querySelectorAll<HTMLButtonElement>("button").forEach((btn) => btn.addEventListener("click", async () => {
        const h = hits[+btn.dataset.i!];
        results.innerHTML = "";
        addr.value = h.label;
        viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(h.lon, h.lat - 0.0016, 170),
          orientation: { heading: 0, pitch: Cesium.Math.toRadians(-40), roll: 0 }, duration: 1.4 });
        await select(h.lon, h.lat);
      }));
    }, 250);
  });

  flyTo("binnenstad");
  if (new URLSearchParams(location.search).has("debug")) (window as any).__twin = { viewer, Cesium, tileset };
  return { viewer, flyTo, select };
}
