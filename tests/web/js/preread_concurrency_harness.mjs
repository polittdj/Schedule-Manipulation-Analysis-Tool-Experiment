/* Execute home.js's bounded-concurrency pre-read against stubs and prove it is EQUIVALENT to the
 * sequential implementation it replaced (ADR-0289).
 *
 * The risk in overlapping the reads is ordering: `/upload` relies on `readable[j]` staying aligned
 * with `meta[j]`, and the operator-facing "could not read these files" notice reads `skipped` in
 * pick order. So this harness re-implements the ORIGINAL sequential algorithm as the oracle and
 * asserts the pooled version produces byte-identical output — over empty, single, clean, and
 * failure-laden selections, with jittered per-file latency so completion order never matches pick
 * order by luck. It also asserts the pool is genuinely BOUNDED (peak <= the cap, which is what keeps
 * a 500-file folder from opening 500 concurrent buffers) and genuinely PARALLEL (peak > 1).
 *
 * Deterministic: the jitter uses a seeded LCG, never Math.random.
 */
import { readFileSync } from "node:fs";

const src = readFileSync("src/schedule_forensics/web/static/home.js", "utf8");
const start = src.indexOf("var PREREAD_CONCURRENCY");
const end = src.indexOf("function skipHint");
if (start < 0 || end < 0 || end <= start) {
  console.log("FAIL could not extract preread() from home.js");
  process.exit(1);
}
const body = src.slice(start, end);

globalThis.File = class {
  constructor(parts, name, opts) {
    this.parts = parts;
    this.name = name;
    this.type = opts.type;
    this.lastModified = opts.lastModified;
  }
};
const mod = new Function(body + "; return { preread, PREREAD_CONCURRENCY };")();

let seed = 12345;
const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) % 8);

function makeFiles(n, failEvery) {
  return Array.from({ length: n }, (_, i) => ({
    name: `f${i}.mpp`,
    type: "application/x",
    lastModified: 1000 + i,
    webkitRelativePath: `dir/f${i}.mpp`,
    arrayBuffer: async () => {
      await new Promise((r) => setTimeout(r, rnd()));
      if (failEvery && i % failEvery === 0) {
        const e = new Error("placeholder");
        e.name = "NotReadableError";
        throw e;
      }
      return new ArrayBuffer(4);
    },
  }));
}

/* the ORIGINAL sequential algorithm — the oracle */
async function sequential(files) {
  const readable = [], meta = [], skipped = [];
  for (const f of files) {
    try {
      const b = await f.arrayBuffer();
      readable.push(new File([b], f.name, { type: f.type, lastModified: f.lastModified }));
      meta.push({ rel: f.webkitRelativePath || "", mtime: f.lastModified || null });
    } catch (e) {
      skipped.push({ path: f.webkitRelativePath || f.name, reason: e.name || "ReadError" });
    }
  }
  return { readable, meta, skipped };
}

const norm = (r) =>
  JSON.stringify({
    readable: r.readable.map((f) => [f.name, f.type, f.lastModified]),
    meta: r.meta,
    skipped: r.skipped,
  });

const fail = (m) => {
  console.log("FAIL " + m);
  process.exit(1);
};

for (const [n, failEvery] of [[0, 0], [1, 0], [5, 0], [25, 4], [100, 7], [13, 1], [7, 1]]) {
  seed = 12345;
  const a = norm(await mod.preread(makeFiles(n, failEvery)));
  seed = 12345;
  const b = norm(await sequential(makeFiles(n, failEvery)));
  if (a !== b) fail(`pooled output differs from sequential at n=${n} failEvery=${failEvery}`);
}

/* bounded AND parallel */
let live = 0, peak = 0;
const probes = Array.from({ length: 30 }, (_, i) => ({
  name: `g${i}`, type: "", lastModified: i, webkitRelativePath: "",
  arrayBuffer: async () => {
    live++; peak = Math.max(peak, live);
    await new Promise((r) => setTimeout(r, 5));
    live--;
    return new ArrayBuffer(1);
  },
}));
await mod.preread(probes);
if (peak > mod.PREREAD_CONCURRENCY) fail(`unbounded: peak ${peak} > cap ${mod.PREREAD_CONCURRENCY}`);
if (peak < 2) fail(`not parallel: peak concurrent reads was ${peak}`);

console.log(`OK equivalent-to-sequential; peak=${peak} cap=${mod.PREREAD_CONCURRENCY}`);
