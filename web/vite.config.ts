import { defineConfig } from "vite";
import { viteStaticCopy } from "vite-plugin-static-copy";

const cesium = "node_modules/cesium/Build/Cesium";

export default defineConfig({
  base: "./", // works under any GitHub Pages sub-path
  define: { CESIUM_BASE_URL: JSON.stringify("./cesium") },
  plugins: [
    viteStaticCopy({
      // strip "node_modules/cesium/Build/Cesium" so files land in dist/cesium/{Workers,ThirdParty,Assets,Widgets}
      targets: [
        ...["Workers", "ThirdParty", "Assets", "Widgets"].map((d) => ({ src: `${cesium}/${d}`, dest: "cesium", rename: { stripBase: 4 } })),
        // MapLibre's worker module and the shared chunk it imports (see src/dashboard.ts)
        ...["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"].map((f) => ({
          src: `node_modules/maplibre-gl/dist/${f}`, dest: "maplibre", rename: { stripBase: true } })),
      ],
    }),
  ],
  build: { chunkSizeWarningLimit: 6000 },
});
