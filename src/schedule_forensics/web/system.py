"""Live machine telemetry for the HUD dock — local reads only, every field nullable.

Feeds ``GET /api/system`` (polled by ``static/sysmon.js``). Data sovereignty: everything here is
a LOCAL read (``/proc``, ``/sys``, ``shutil``, ``ctypes`` Win32 calls, short local subprocesses —
``nvidia-smi`` / ``vm_stat`` / ``powershell`` counters — and the optional ``psutil`` package) —
nothing touches the network, so Law 1 is untouched.

Design (ADR-0147, the "telemetry works on the operator's Windows box" fix):

* **Fast collectors** run inline per request and are instant on every OS: CPU% and RAM via
  ``psutil`` when present, else native stdlib paths — ``/proc`` on Linux, ``ctypes``
  (``GetSystemTimes`` / ``GlobalMemoryStatusEx``) on Windows, ``sysctl``/``vm_stat`` on macOS.
  Disk is ``shutil.disk_usage`` everywhere. CPU% is delta-based between polls (no sleeping
  in-request); the very first sample reports 0.0 and becomes real from the second poll.
* **Slow probes** (GPU via ``nvidia-smi`` or the Windows GPU performance counters; CPU
  temperature via sensors / WMI thermal zone) can take hundreds of ms to seconds, so they run
  on a lazily-started background daemon thread and ``snapshot()`` serves the latest cached
  values instantly. Probes that keep failing stop being retried (``_MAX_FAILURES``).
* Any value a platform cannot provide is ``None`` and the widget renders "—" instead of failing.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 — fixed local argv only (nvidia-smi / vm_stat / powershell)
import sys
import threading
from typing import Any

try:  # optional enhancer — NOT a hard runtime dependency (see pyproject [monitor] extra)
    import psutil
except Exception:  # pragma: no cover - absence is a supported configuration
    psutil = None  # type: ignore[assignment, unused-ignore]  # Any when untyped, module when typed

_GPU_NONE: dict[str, Any] = {
    "name": None,
    "util_percent": None,
    "mem_percent": None,
    "temp_c": None,
}

#: previous (busy, total) CPU-time pair for delta-based CPU% without sleeping.
_prev_cpu: tuple[int, int] | None = None

# ── fast collectors: CPU% ──────────────────────────────────────────────────────────────────


def _delta_percent(busy: int, total: int) -> float | None:
    """Percent from the previous (busy, total) sample; 0.0 on the very first call."""
    global _prev_cpu
    prev, _prev_cpu = _prev_cpu, (busy, total)
    if prev is None:
        return 0.0  # first sample has no delta yet; real from the next poll
    dt = total - prev[1]
    if dt <= 0:
        return 0.0
    return round(100.0 * (busy - prev[0]) / dt, 1)


def _win_cpu_percent() -> float | None:
    """Windows CPU% from ``GetSystemTimes`` (stdlib ctypes; kernel time includes idle)."""
    try:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:  # pragma: no cover - non-Windows
            return None
        idle = ctypes.c_uint64()
        kernel = ctypes.c_uint64()
        user = ctypes.c_uint64()
        ok = windll.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        )
        if not ok:
            return None
        total = int(kernel.value) + int(user.value)
        busy = total - int(idle.value)
        return _delta_percent(busy, total)
    except Exception:  # pragma: no cover - defensive: telemetry must never raise
        return None


def _linux_cpu_percent() -> float | None:
    try:
        with open("/proc/stat", encoding="ascii") as fh:
            parts = fh.readline().split()[1:]
        nums = [int(x) for x in parts]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
        total = sum(nums)
        return _delta_percent(total - idle, total)
    except (OSError, ValueError, IndexError):
        return None


def _cpu_percent() -> float | None:
    if psutil is not None:
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:  # pragma: no cover  # nosec B110 - best-effort, native fallback below
            pass
    if os.name == "nt":
        return _win_cpu_percent()
    return _linux_cpu_percent()  # macOS has no honest stdlib instant CPU%; psutil covers it


# ── fast collectors: memory ────────────────────────────────────────────────────────────────


def _win_memory() -> dict[str, Any]:
    """Windows RAM from ``GlobalMemoryStatusEx`` (stdlib ctypes)."""
    try:
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:  # pragma: no cover - non-Windows
            return {"total_gb": None, "used_gb": None, "percent": None}

        class _MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        stat = _MemoryStatusEx()
        stat.dwLength = ctypes.sizeof(stat)
        if not windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return {"total_gb": None, "used_gb": None, "percent": None}
        total = int(stat.ullTotalPhys)
        used = total - int(stat.ullAvailPhys)
        return {
            "total_gb": round(total / 2**30, 1),
            "used_gb": round(used / 2**30, 1),
            "percent": round(100.0 * used / total, 1) if total else None,
        }
    except Exception:  # pragma: no cover - defensive: telemetry must never raise
        return {"total_gb": None, "used_gb": None, "percent": None}


def _linux_memory() -> dict[str, Any]:
    try:
        info: dict[str, int] = {}
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                info[key] = int(rest.split()[0])  # kB
        total = info["MemTotal"]
        avail = info.get("MemAvailable", info.get("MemFree", 0))
        used = total - avail
        return {
            "total_gb": round(total / 2**20, 1),
            "used_gb": round(used / 2**20, 1),
            "percent": round(100.0 * used / total, 1) if total else None,
        }
    except (OSError, KeyError, ValueError):
        return {"total_gb": None, "used_gb": None, "percent": None}


def _mac_memory() -> dict[str, Any]:  # pragma: no cover - exercised on macOS only
    """macOS RAM from ``sysctl hw.memsize`` + ``vm_stat`` (both local, ~20 ms)."""
    try:
        total = int(
            subprocess.run(  # nosec B603 B607 - fixed argv, local binary, no shell
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2
            ).stdout.strip()
        )
        vm = subprocess.run(  # nosec B603 B607 - fixed argv, local binary, no shell
            ["vm_stat"], capture_output=True, text=True, timeout=2
        ).stdout
        used = parse_vm_stat_used_bytes(vm)
        if used is None:
            return {"total_gb": round(total / 2**30, 1), "used_gb": None, "percent": None}
        return {
            "total_gb": round(total / 2**30, 1),
            "used_gb": round(used / 2**30, 1),
            "percent": round(100.0 * used / total, 1) if total else None,
        }
    except Exception:
        return {"total_gb": None, "used_gb": None, "percent": None}


def parse_vm_stat_used_bytes(vm_stat_output: str) -> int | None:
    """Used bytes from ``vm_stat`` output: (active + wired + compressed) x page size."""
    try:
        page = 4096
        first = vm_stat_output.splitlines()[0] if vm_stat_output else ""
        if "page size of" in first:
            page = int(first.split("page size of")[1].split()[0])
        pages: dict[str, int] = {}
        for line in vm_stat_output.splitlines()[1:]:
            key, _, rest = line.partition(":")
            rest = rest.strip().rstrip(".")
            if rest.isdigit():
                pages[key.strip().lower()] = int(rest)
        needed = ("pages active", "pages wired down")
        if not all(k in pages for k in needed):
            return None
        used_pages = (
            pages["pages active"]
            + pages["pages wired down"]
            + pages.get("pages occupied by compressor", 0)
        )
        return used_pages * page
    except (ValueError, IndexError):
        return None


def _memory() -> dict[str, Any]:
    if psutil is not None:
        try:
            vm = psutil.virtual_memory()
            return {
                "total_gb": round(float(vm.total) / 2**30, 1),
                "used_gb": round(float(vm.total - vm.available) / 2**30, 1),
                "percent": round(float(vm.percent), 1),
            }
        except Exception:  # pragma: no cover  # nosec B110 - best-effort, native fallback below
            pass
    if os.name == "nt":
        return _win_memory()
    if sys.platform == "darwin":  # pragma: no cover - macOS only
        return _mac_memory()
    return _linux_memory()


# ── fast collectors: disk ──────────────────────────────────────────────────────────────────


def _disk() -> dict[str, Any]:
    try:
        root = "C:\\" if os.name == "nt" else "/"
        du = shutil.disk_usage(root)
        return {
            "total_gb": round(du.total / 2**30, 1),
            "used_gb": round(du.used / 2**30, 1),
            "percent": round(100.0 * du.used / du.total, 1) if du.total else None,
        }
    except OSError:  # pragma: no cover
        return {"total_gb": None, "used_gb": None, "percent": None}


# ── slow probes (GPU, CPU temperature): background-refreshed, served from cache ──────────────

#: refresh cadence for the slow probes; the poll loop reads the cache instantly.
_SLOW_INTERVAL = 5.0
#: a probe that fails this many times in a row stops being retried (no powershell respawn churn)
_MAX_FAILURES = 3

_slow_lock = threading.Lock()
_slow_started = False
_slow_cache: dict[str, Any] = {"gpu": dict(_GPU_NONE), "cpu_temp_c": None}
_slow_failures = {"gpu": 0, "temp": 0}


def parse_nvidia_smi_line(line: str) -> dict[str, Any]:
    """Per-field-tolerant parse of one ``nvidia-smi --query-gpu`` CSV line ("[N/A]" → None)."""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 5:
        return dict(_GPU_NONE)

    def _f(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None

    util = _f(parts[1])
    mem_used, mem_total = _f(parts[2]), _f(parts[3])
    mem_pct = round(100.0 * mem_used / mem_total, 1) if mem_used is not None and mem_total else None
    return {
        "name": parts[0] or None,
        "util_percent": util,
        "mem_percent": mem_pct,
        "temp_c": _f(parts[4]),
    }


def _find_nvidia_smi() -> str | None:
    """Locate nvidia-smi: PATH first, then the known Windows install locations."""
    smi = shutil.which("nvidia-smi")
    if smi:
        return smi
    if os.name == "nt":  # pragma: no cover - Windows only
        for candidate in (
            os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "System32", "nvidia-smi.exe"),
            os.path.join(
                os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                "NVIDIA Corporation",
                "NVSMI",
                "nvidia-smi.exe",
            ),
        ):
            if os.path.isfile(candidate):
                return candidate
    return None


def _probe_gpu() -> dict[str, Any]:
    """One GPU sample: nvidia-smi (any OS) → Windows perf counters (vendor-neutral) → None."""
    smi = _find_nvidia_smi()
    if smi:
        try:
            out = subprocess.run(  # nosec B603 - fixed argv, local binary, no shell
                [
                    smi,
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
            if line:
                return parse_nvidia_smi_line(line)
        except Exception:  # nosec B110 - fall through to the vendor-neutral probe
            pass
    if os.name == "nt":  # pragma: no cover - Windows only
        return _win_gpu_counters()
    return dict(_GPU_NONE)


def _win_gpu_counters() -> dict[str, Any]:  # pragma: no cover - Windows only
    """Vendor-neutral Windows GPU probe (AMD/Intel/NVIDIA) via the WDDM performance counters.

    Utilization only — the counters expose no total-VRAM or temperature, so those stay None
    (localized counter names on non-English Windows also fail closed to None)."""
    script = (
        "$u=(Get-Counter '\\GPU Engine(*engtype_3D)\\Utilization Percentage' -ErrorAction Stop)"
        ".CounterSamples | Measure-Object -Property CookedValue -Sum | "
        "Select-Object -ExpandProperty Sum; "
        "$n=(Get-CimInstance Win32_VideoController | Select-Object -First 1 "
        '-ExpandProperty Name); Write-Output "$([math]::Round($u,1))`n$n"'
    )
    try:
        out = subprocess.run(  # nosec B603 B607 - fixed local powershell argv, no shell string
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        lines = [ln.strip() for ln in out.stdout.strip().splitlines() if ln.strip()]
        if not lines:
            return dict(_GPU_NONE)
        util = float(lines[0].replace(",", "."))  # tolerate comma-decimal locales
        name = lines[1] if len(lines) > 1 else None
        return {
            "name": name,
            "util_percent": round(min(100.0, util), 1),
            "mem_percent": None,
            "temp_c": None,
        }
    except Exception:
        return dict(_GPU_NONE)


def _probe_cpu_temp() -> float | None:
    if psutil is not None:
        try:
            temps = psutil.sensors_temperatures()
            for name in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                if temps.get(name):
                    return round(float(temps[name][0].current), 1)
            for entries in temps.values():
                if entries:
                    return round(float(entries[0].current), 1)
        except Exception:  # pragma: no cover  # nosec B110 - best-effort, native fallbacks below
            pass
    try:  # Linux sysfs
        for zone in sorted(os.listdir("/sys/class/thermal")):
            if zone.startswith("thermal_zone"):
                with open(f"/sys/class/thermal/{zone}/temp", encoding="ascii") as fh:
                    milli = int(fh.read().strip())
                if 1000 < milli < 150000:
                    return round(milli / 1000.0, 1)
    except (OSError, ValueError):
        pass
    if os.name == "nt":  # pragma: no cover - Windows only
        return _win_cpu_temp()
    return None


def _win_cpu_temp() -> float | None:  # pragma: no cover - Windows only
    """ACPI thermal zone via WMI (tenths of Kelvin); many boards don't expose it → None."""
    script = (
        "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
        "-ErrorAction Stop | Select-Object -First 1 -ExpandProperty CurrentTemperature)"
    )
    try:
        out = subprocess.run(  # nosec B603 B607 - fixed local powershell argv, no shell string
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        raw = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
        tenths_kelvin = float(raw.replace(",", "."))
        celsius = tenths_kelvin / 10.0 - 273.15
        return round(celsius, 1) if -30.0 < celsius < 150.0 else None
    except Exception:
        return None


def _slow_loop() -> None:  # pragma: no cover - timing loop; probes are tested directly
    while True:
        if _slow_failures["gpu"] < _MAX_FAILURES:
            gpu = _probe_gpu()
            _slow_failures["gpu"] = 0 if gpu != _GPU_NONE else _slow_failures["gpu"] + 1
            _slow_cache["gpu"] = gpu
        if _slow_failures["temp"] < _MAX_FAILURES:
            temp = _probe_cpu_temp()
            _slow_failures["temp"] = 0 if temp is not None else _slow_failures["temp"] + 1
            _slow_cache["cpu_temp_c"] = temp
        threading.Event().wait(_SLOW_INTERVAL)


def _ensure_slow_thread() -> None:
    global _slow_started
    with _slow_lock:
        if _slow_started:
            return
        _slow_started = True
        threading.Thread(target=_slow_loop, name="sf-telemetry", daemon=True).start()


# ── public API ─────────────────────────────────────────────────────────────────────────────


def snapshot() -> dict[str, Any]:
    """One telemetry sample; instant and safe on every platform (missing values are ``None``).

    Fast fields are read inline; GPU and CPU temperature come from the background probe cache
    (first request starts the probe thread, so those may be ``None`` for the first seconds)."""
    _ensure_slow_thread()
    return {
        "cpu": {
            "percent": _cpu_percent(),
            "cores": os.cpu_count(),
            "temp_c": _slow_cache["cpu_temp_c"],
        },
        "memory": _memory(),
        "disk": _disk(),
        "gpu": dict(_slow_cache["gpu"]),
        "platform": sys.platform,
        "psutil": psutil is not None,
    }
