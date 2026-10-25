// Compress the exported 3D Tiles content in place with meshopt (quantization + EXT_meshopt_compression).
// Run after `python -m delft_twin.mesh`, which regenerates the uncompressed tiles.
import { execFileSync } from "node:child_process";
import { readdirSync, renameSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const dir = join(root, "public", "data", "tiles");
const cli = join(root, "node_modules", "@gltf-transform", "cli", "bin", "cli.js");

let before = 0, after = 0;
for (const f of readdirSync(dir).filter((n) => n.endsWith(".glb"))) {
  const src = join(dir, f);
  const tmp = src.replace(/\.glb$/, ".tmp.glb");
  before += statSync(src).size;
  execFileSync(process.execPath, [cli, "meshopt", src, tmp, "--level", "medium"], { stdio: "inherit" });
  renameSync(tmp, src);
  after += statSync(src).size;
  console.log(`${f}: ${(statSync(src).size / 1e6).toFixed(2)} MB`);
}
console.log(`total ${(before / 1e6).toFixed(1)} MB -> ${(after / 1e6).toFixed(1)} MB`);
