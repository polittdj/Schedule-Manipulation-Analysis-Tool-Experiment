# ADR-0147 — Telemetry that works on the operator's machine: native Windows/macOS collectors, probe cache, default-on dock

## Status

Accepted. Fixes the operator-reported defect against ADR-0146's telemetry layer.

## Context

The operator reported the CPU / RAM / VRAM / disk / GPU readouts "not working properly." A live
browser verification (Playwright + Chromium against the running app) showed the ADR-0146
mechanics working end-to-end on Linux — chips render, values refresh each poll, details expand,
no console errors. The failures were **platform coverage and discoverability**, not JS:

1. **Windows had no native code path at all.** The stdlib collectors read `/proc` and `/sys`,
   which don't exist on Windows. Everything except disk depended entirely on `psutil` — an
   optional, best-effort installer extra. If that one `pip install` failed, CPU%, RAM, and both
   temperatures were permanently "—" on the exact machine the tool is deployed to.
2. **CPU temperature on Windows** could never work: `psutil.sensors_temperatures()` does not
   exist on Windows, and the only fallback was Linux sysfs.
3. **GPU/VRAM** required `nvidia-smi` on `PATH` — missing the legacy NVIDIA install directory
   and every AMD/Intel GPU. A single unparseable field (`[N/A]` utilization, common on
   laptops) blanked the whole GPU card instead of just that field.
4. **Discoverability:** outside JARVIS the dock defaulted OFF behind a small muted
   "◉ telemetry" button — reading as "broken" rather than "hidden". The operator's directive
   was readouts "in small windows … throughout", i.e. visible by default.
5. Slow probes ran inline in the request: a cold `nvidia-smi` (or any future counter query)
   could stall the 2 s poll loop.

## Decision

`web/system.py` restructured (same response shape; `/api/system` unchanged for clients):

- **Fast collectors, native per OS, psutil now purely an enhancer:** CPU% via
  `ctypes GetSystemTimes` deltas on Windows and `/proc/stat` deltas on Linux (shared
  `_delta_percent`); RAM via `ctypes GlobalMemoryStatusEx` on Windows, `/proc/meminfo` on
  Linux, `sysctl hw.memsize` + `vm_stat` on macOS (`parse_vm_stat_used_bytes`, unit-tested).
  macOS CPU% deliberately stays psutil-only rather than shipping a load-average masquerading
  as a percentage (fidelity: no dishonest numbers).
- **Slow probes move off the request path:** GPU and CPU temperature are refreshed every 5 s
  by a lazily-started daemon thread and served from a cache — `snapshot()` never blocks on a
  subprocess. A probe that fails `_MAX_FAILURES` (3) consecutive times stops being retried.
- **GPU coverage:** `nvidia-smi` located via `PATH` **plus** the known Windows install dirs
  (`System32`, the legacy `NVSMI` dir); CSV parsing is per-field tolerant (`[N/A]` → that field
  None, the rest keep their values). Where nvidia-smi is unavailable on Windows, a
  vendor-neutral fallback reads the WDDM GPU performance counters via one PowerShell call
  (utilization + adapter name; VRAM%/temp stay None — the counters don't expose them; localized
  counter names fail closed to None).
- **CPU temperature on Windows:** ACPI thermal zone via WMI (`MSAcpi_ThermalZoneTemperature`),
  best-effort in the probe thread — many consumer boards don't expose it; sanity-ranged, None
  otherwise.
- **Dock default-ON in every theme** (`sysmon.js wanted()` = `pref() !== "off"`); the explicit
  hide still persists. Fetches are `cache: "no-store"` + the endpoint sends
  `Cache-Control: no-store`, and non-OK responses are treated as failures (keep last values).

Law 1 unchanged: every collector is a local read (`ctypes` Win32 calls, `/proc`, `/sys`,
`shutil`, fixed-argv local subprocesses); nothing network-facing was added.

## Consequences

- On a plain Windows box with **no psutil at all**, CPU%, RAM, and disk now work stdlib-only;
  NVIDIA machines get full GPU/VRAM/temp, AMD/Intel machines get utilization + name.
- The readouts are visible on first launch in every theme — no hidden toggle to discover.
- Verified two ways: 21 HUD-layer tests (probe parsers, cache, non-Windows degradation,
  no-store, default-on) plus a scripted real-browser (Chromium) end-to-end run — default
  visibility, live refresh, expand cards, hide-persists-across-reload.
- Wheel + all nine installers regenerated (the embedded wheel must carry the fixed module).
