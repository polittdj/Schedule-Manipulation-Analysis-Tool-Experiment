"""Live machine telemetry for the HUD dock — local reads only, every field nullable.

Feeds ``GET /api/system`` (polled by ``static/sysmon.js``). Data sovereignty: everything here is
a LOCAL read (``/proc``, ``/sys``, ``shutil``, an optional local ``nvidia-smi`` subprocess, the
optional ``psutil`` package) — nothing touches the network, so Law 1 is untouched. Collectors are
stdlib-first with ``psutil`` as an optional enhancer (Windows/macOS CPU%/temps); any value a
platform cannot provide is ``None`` and the widget renders "—" instead of failing. CPU% is
computed from successive ``/proc/stat`` deltas kept in module state (no sleeping in-request).
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 — used only for a fixed, local nvidia-smi argv (no shell)
import sys
from typing import Any

try:  # optional enhancer — NOT a hard runtime dependency (see pyproject [monitor] extra)
    import psutil
except Exception:  # pragma: no cover - absence is a supported configuration
    psutil = None  # type: ignore[assignment, unused-ignore]  # Any when untyped, module when typed

#: previous (busy, total) jiffies from /proc/stat, for delta-based CPU% without sleeping.
_prev_cpu: tuple[int, int] | None = None


def _cpu_percent() -> float | None:
    global _prev_cpu
    if psutil is not None:
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:  # pragma: no cover  # nosec B110 - best-effort, stdlib fallback below
            pass
    try:
        with open("/proc/stat", encoding="ascii") as fh:
            parts = fh.readline().split()[1:]
        nums = [int(x) for x in parts]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
        total = sum(nums)
        busy = total - idle
        if _prev_cpu is not None:
            dt = total - _prev_cpu[1]
            db = busy - _prev_cpu[0]
            _prev_cpu = (busy, total)
            if dt > 0:
                return round(100.0 * db / dt, 1)
        _prev_cpu = (busy, total)
        return 0.0  # first sample has no delta yet
    except OSError:
        return None


def _memory() -> dict[str, Any]:
    if psutil is not None:
        try:
            vm = psutil.virtual_memory()
            return {
                "total_gb": round(vm.total / 2**30, 1),
                "used_gb": round((vm.total - vm.available) / 2**30, 1),
                "percent": round(vm.percent, 1),
            }
        except Exception:  # pragma: no cover  # nosec B110 - best-effort, stdlib fallback below
            pass
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


def _cpu_temp() -> float | None:
    if psutil is not None:
        try:
            temps = psutil.sensors_temperatures()
            for name in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                if temps.get(name):
                    return round(float(temps[name][0].current), 1)
            for entries in temps.values():
                if entries:
                    return round(float(entries[0].current), 1)
        except Exception:  # pragma: no cover  # nosec B110 - best-effort, sysfs fallback below
            pass
    try:  # Linux sysfs fallback
        for zone in sorted(os.listdir("/sys/class/thermal")):
            if zone.startswith("thermal_zone"):
                with open(f"/sys/class/thermal/{zone}/temp", encoding="ascii") as fh:
                    milli = int(fh.read().strip())
                if 1000 < milli < 150000:
                    return round(milli / 1000.0, 1)
    except (OSError, ValueError):
        pass
    return None


def _gpu() -> dict[str, Any]:
    """NVIDIA telemetry via a short local ``nvidia-smi`` call; all-None when unavailable."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {"name": None, "util_percent": None, "mem_percent": None, "temp_c": None}
    try:
        out = subprocess.run(  # nosec B603 - fixed argv, local binary, no shell
            [
                smi,
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
        name, util, mem_used, mem_total, temp = (p.strip() for p in line.split(","))
        mem_pct = round(100.0 * float(mem_used) / float(mem_total), 1) if float(mem_total) else None
        return {
            "name": name,
            "util_percent": float(util),
            "mem_percent": mem_pct,
            "temp_c": float(temp),
        }
    except Exception:  # any parse/timeout issue → graceful "no GPU data"
        return {"name": None, "util_percent": None, "mem_percent": None, "temp_c": None}


def snapshot() -> dict[str, Any]:
    """One telemetry sample; safe on every platform (missing values are ``None``)."""
    return {
        "cpu": {
            "percent": _cpu_percent(),
            "cores": os.cpu_count(),
            "temp_c": _cpu_temp(),
        },
        "memory": _memory(),
        "disk": _disk(),
        "gpu": _gpu(),
        "platform": sys.platform,
        "psutil": psutil is not None,
    }
