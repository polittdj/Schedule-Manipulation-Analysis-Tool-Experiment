"""Headless exhibit-pack generator — ``schedule-forensics-report``.

Imports the exhibits library directly; NEVER starts or needs the web server (the launcher's
browser-heartbeat watchdog would kill a resident job anyway — a scheduled task needs no
browser and no server).

Exit codes (documented here and in ``--help``):

* ``0`` — success.
* ``2`` — input/ingest hard-fail (unreadable file / invalid payload).
* ``3`` — terminus not designated where required.
* ``4`` — engine artifacts missing: the CP-basis engine (driving tree, CIC, τ-b, null-model
  churn, recompute deltas) is not built yet, so ``--inputs`` runs cannot produce a truthful
  payload. Until that lands (see ``audit/PARK-LIST.md``), render from a prebuilt payload via
  ``--payload`` (the golden fixtures under ``tests/exhibits/fixtures/`` are valid inputs).
* ``5`` — output directory not empty and ``--force`` not given.

Determinism: ``run_id`` = sha256(sorted input hashes + canonicalized config)[:16]; no
timestamps in filenames, metadata, or content — two identical runs are byte-identical.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schedule_forensics.exhibits.csvout import CSV_WRITERS
from schedule_forensics.exhibits.payload import canonical_json, load_payload
from schedule_forensics.exhibits.render_svg import EXHIBITS
from schedule_forensics.exhibits.report_html import render_report
from schedule_forensics.logging_redaction import configure_logging
from schedule_forensics.net_guard import assert_local_only

EXIT_OK = 0
EXIT_INGEST = 2
EXIT_NO_TERMINUS = 3
EXIT_ENGINE_MISSING = 4
EXIT_OUT_NOT_EMPTY = 5


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="schedule-forensics-report",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--inputs",
        nargs="*",
        default=[],
        help="ordered .mpp/.xml set (REQUIRES the CP-basis engine — exit 4 until "
        "it lands; use --payload meanwhile)",
    )
    ap.add_argument("--payload", help="prebuilt exhibit-payload JSON to render (deterministic)")
    ap.add_argument("--out", required=True, help="output directory (must be empty unless --force)")
    ap.add_argument(
        "--target-uid", action="append", type=int, default=[], help="terminus UID (repeatable)"
    )
    ap.add_argument("--basis", choices=["correct", "parity:msp"], default="correct")
    ap.add_argument("--format", choices=["all", "html", "svg", "csv"], default="all")
    ap.add_argument("--json-summary", action="store_true", help="write summary.json")
    ap.add_argument("--force", action="store_true", help="allow a non-empty --out")
    return ap


def main(argv: list[str] | None = None) -> int:
    # Law 1, same as the other entry points (launcher.main / create_app): redacting
    # logging active before any library can log, and a fail-closed egress assertion —
    # the report generator refuses to run at all with an egress-capable runtime
    # (CUIEgressError propagates: loud, non-zero exit, nothing written).
    configure_logging()
    assert_local_only()
    args = _parser().parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()) and not args.force:
        print(f"refusing: output dir {out} is not empty (use --force)", file=sys.stderr)
        return EXIT_OUT_NOT_EMPTY

    if args.payload:
        try:
            text = Path(args.payload).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"cannot read payload: {exc}", file=sys.stderr)
            return EXIT_INGEST
        try:
            payload = load_payload(text)
        except ValueError as exc:
            print(f"invalid payload: {exc}", file=sys.stderr)
            return EXIT_INGEST
    elif args.inputs:
        for f in args.inputs:
            if not Path(f).exists():
                print(f"input not found: {f}", file=sys.stderr)
                return EXIT_INGEST
        if not args.target_uid:
            print(
                "terminus not designated: pass --target-uid (engine hard-fail rule)",
                file=sys.stderr,
            )
            return EXIT_NO_TERMINUS
        print(
            "engine artifacts missing: the CP-basis engine (driving tree, CIC, tau-b, "
            "null-model churn, recompute deltas) is not built yet; render from --payload "
            "until it lands (audit/PARK-LIST.md).",
            file=sys.stderr,
        )
        return EXIT_ENGINE_MISSING
    else:
        print("nothing to do: pass --payload or --inputs", file=sys.stderr)
        return EXIT_INGEST

    serialized = canonical_json(payload)
    (out / "payload.json").write_text(serialized, encoding="utf-8")
    written: list[str] = ["payload.json"]
    for ex_id, (stem, renderer) in EXHIBITS.items():
        if args.format in ("all", "svg"):
            name = f"{ex_id}_{stem}.svg"
            (out / name).write_text(renderer(payload), encoding="utf-8")
            written.append(name)
        if args.format in ("all", "csv"):
            name = f"{ex_id}_{stem}.csv"
            (out / name).write_text(CSV_WRITERS[ex_id](payload), encoding="utf-8")
            written.append(name)
    if args.format in ("all", "html"):
        (out / "report.html").write_text(render_report(payload), encoding="utf-8")
        written.append("report.html")
    if args.json_summary:
        summary = {
            "run_id": payload.manifest.run_id,
            "cic_per_update": {u.status_date: u.cic for u in payload.update_summaries},
            "attributable_churn_per_transition": {
                f"{t.from_status_date}->{t.to_status_date}": t.attributable_churn
                for t in payload.transitions
            },
            "unmatched_count": payload.manifest.unmatched_count,
            "nonzero_recompute_delta_files": [
                f.path
                for f in payload.manifest.files
                if (f.recompute_delta_nonzero_task_count or 0) > 0
            ],
            "exhibits": sorted(written),
        }
        (out / "summary.json").write_text(
            json.dumps(summary, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
