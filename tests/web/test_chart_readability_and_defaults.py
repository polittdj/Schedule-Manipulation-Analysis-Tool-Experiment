"""Operator live-test batch (2026-07-13): AI defaults + chart-toolbar placement + label de-overlap.

- #3 the CUI AI comes up on Ollama with qwen2.5:7b-instruct by default, still CLASSIFIED + loopback.
- #1 the chart toolbar (.cf-bar) is an in-flow row, never absolutely overlaid on the plotted data.
- #4 the trend line charts de-overlap their inline value labels and keep every value on hover.
"""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.ai.backend import AIConfig, Classification

STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


def test_ai_defaults_are_cui_local_ollama_qwen() -> None:
    cfg = AIConfig()
    assert cfg.classification is Classification.CLASSIFIED  # CUI by default
    assert cfg.backend == "ollama"
    assert cfg.model == "qwen2.5:7b-instruct"
    assert cfg.endpoint == "http://127.0.0.1:11434"  # loopback-only


def test_chart_toolbar_is_in_flow_not_over_the_data() -> None:
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    # the toolbar rule no longer positions .cf-bar absolutely over the chart; it flows above it
    marker = ".cf-bar { display: flex;"
    assert marker in css
    bar_rule = css[css.index(marker) : css.index(marker) + 200]
    assert "position: absolute" not in bar_rule
    assert "margin: 0 6px 4px auto" in bar_rule  # pushed to the right, in its own row


def test_trend_line_charts_de_overlap_labels_and_keep_hover() -> None:
    js = (STATIC / "trend.js").read_text(encoding="utf-8")
    # the greedy de-overlap helper guards every inline value label
    assert js.count("function labelFits(lx, ly)") >= 3  # multiLine, line, varianceTrend
    assert "if (labelFits(x(i), ly))" in js
    # a de-overlapped value is never lost: the variance markers gained a hover <title>
    assert "hover call-out so a de-overlapped value is never lost" in js
