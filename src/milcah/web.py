"""FastAPI app: read-only viewer for saved coherence snapshots (FR10).

Single-file: routes + templates + CSS, HTML built from Python f-strings
with html.escape on every interpolation — the same minimal pattern as the
family's other browsers (Mahalath, Hoglah). No templating dependency.

The viewer sits on the same `Store` seam as the CLI (`JsonFileStore` or
`MongoStore`), so whatever `milcah metrics --save` wrote is what it shows:
a framework index, each framework's coherence **trend over time** (FR10)
rendered as dependency-free inline SVG sparklines, and full snapshot
detail. Strictly read-only — analysis stays in the CLI.

Security posture: bind to 127.0.0.1 by default. There is no auth; the
operator runs it locally, browser on the same host.

Requires the ``web`` extra: ``pip install milcah[web]``.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from milcah.persistence import TREND_METRICS, Snapshot, Store, compute_trend

# Metrics where an increase is an improvement; the rest are burdens/debt,
# where a decrease is the good direction (FR7/FR9 reading of the trend).
_HIGHER_IS_BETTER = {"global_coherence", "ontological_completeness"}

_CSS = """
:root {
  --bg: #f6f7f9; --surface: #ffffff; --ink: #1c2128; --muted: #667085;
  --line: #e3e6ea; --line-soft: #edf0f3; --accent: #2f5fd0; --accent-soft: #e8eefc;
  --good: #14803c; --bad: #c22736;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12151b; --surface: #1a1e26; --ink: #e5e8ee; --muted: #97a0af;
    --line: #2a3039; --line-soft: #232833; --accent: #7c9cff; --accent-soft: #232c45;
    --good: #7edc9f; --bad: #ff9aa4;
  }
}
* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0;
       line-height: 1.55; color: var(--ink); background: var(--bg); font-size: 15px; }
main { max-width: 1100px; margin: 0 auto; padding: 1.2em 1.2em 3em; }
a { color: var(--accent); }
h1 { font-size: 1.5em; margin: 0.6em 0 0.5em; }
h2 { font-size: 1.05em; margin: 1.6em 0 0.5em; text-transform: uppercase;
     letter-spacing: 0.05em; color: var(--muted); font-weight: 600; }
header { position: sticky; top: 0; z-index: 10; background: var(--surface);
         border-bottom: 1px solid var(--line); }
header nav { max-width: 1100px; margin: 0 auto; padding: 0.55em 1.2em;
             display: flex; align-items: center; gap: 0.6em; }
.brand { font-weight: 700; color: var(--ink); text-decoration: none; }
.dbname { margin-left: auto; color: var(--muted); font-size: 0.85em;
          font-family: ui-monospace, "SF Mono", Menlo, monospace; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; background: var(--surface);
        border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 0.55em 0.8em; border-bottom: 1px solid var(--line-soft);
         vertical-align: middle; }
tr:last-child td { border-bottom: none; }
th { background: var(--line-soft); font-weight: 600; font-size: 0.85em;
     text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
tr:hover td { background: var(--line-soft); }
@media (max-width: 720px) { table { display: block; overflow-x: auto; } }
code { background: var(--line-soft); padding: 0.1em 0.4em; border-radius: 4px;
       font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.92em; }
pre { background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
      padding: 0.8em 1em; overflow-x: auto; white-space: pre-wrap; word-break: break-word;
      font-size: 0.88em; }
details { margin: 0.6em 0; }
summary { cursor: pointer; color: var(--muted); }
.muted { color: var(--muted); }
.num { font-variant-numeric: tabular-nums; }
.delta-good { color: var(--good); font-weight: 600; }
.delta-bad { color: var(--bad); font-weight: 600; }
.delta-flat { color: var(--muted); }
.spark { vertical-align: middle; }
.spark polyline { fill: none; stroke: var(--accent); stroke-width: 1.5; }
.spark circle { fill: var(--accent); }
.kvbox th { width: 14em; }
"""


def _base(title: str, body: str, store_label: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — Milcah</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <nav>
    <a class="brand" href="/">Milcah</a>
    <span class="muted">coherence snapshots</span>
    <span class="dbname">{escape(store_label)}</span>
  </nav>
</header>
<main>
{body}
</main>
</body>
</html>"""


def _sparkline(values: list[Any], width: int = 130, height: int = 28) -> str:
    """A dependency-free inline-SVG sparkline; gaps (None) are skipped."""
    points = [(i, float(v)) for i, v in enumerate(values) if isinstance(v, (int, float))]
    if len(points) < 2:
        return '<span class="muted">—</span>'
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    x_span = (x_hi - x_lo) or 1
    y_span = (y_hi - y_lo) or 1
    pad = 3
    coords = " ".join(
        f"{pad + (x - x_lo) / x_span * (width - 2 * pad):.1f},"
        f"{height - pad - (y - y_lo) / y_span * (height - 2 * pad):.1f}"
        for x, y in points
    )
    last = coords.rsplit(" ", 1)[-1]
    lx, ly = last.split(",")
    return (
        f'<svg class="spark" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="trend">'
        f'<polyline points="{coords}"/><circle cx="{lx}" cy="{ly}" r="2.5"/></svg>'
    )


def _delta_cell(metric: str, delta: float) -> str:
    if not delta:
        return '<span class="delta-flat">→ 0</span>'
    arrow = "↑" if delta > 0 else "↓"
    improved = (delta > 0) == (metric in _HIGHER_IS_BETTER)
    css = "delta-good" if improved else "delta-bad"
    return f'<span class="{css}">{arrow} {delta:+g}</span>'


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:g}"
    return escape(str(value))


def create_app(store: Store, store_label: str = "snapshots") -> FastAPI:
    """Build the viewer over any FR10 `Store` (JsonFileStore, MongoStore, ...)."""
    app = FastAPI(title="Milcah", description="Read-only coherence snapshot viewer")
    app.state.store = store

    def _history_or_404(framework_id: str) -> list[Snapshot]:
        snaps = store.history(framework_id)
        if not snaps:
            raise HTTPException(404, f"no snapshots for framework: {framework_id}")
        return snaps

    @app.get("/api/frameworks")
    def api_frameworks() -> dict[str, Any]:
        return {"ok": True, "frameworks": store.frameworks()}

    @app.get("/api/frameworks/{framework_id}/trend")
    def api_trend(framework_id: str) -> dict[str, Any]:
        snaps = _history_or_404(framework_id)
        return {"ok": True, "trend": compute_trend(snaps)}

    @app.get("/api/frameworks/{framework_id}/snapshots/{snapshot_id}")
    def api_snapshot(framework_id: str, snapshot_id: str) -> dict[str, Any]:
        snap = store.load(framework_id, snapshot_id)
        if snap is None:
            raise HTTPException(404, f"snapshot not found: {snapshot_id}")
        return {"ok": True, "snapshot": snap.to_jsonable()}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        rows = []
        for fw in store.frameworks():
            metrics = fw.get("latest_metrics") or {}
            rows.append(f"""
<tr>
  <td><a href="/frameworks/{escape(fw["framework_id"])}">{escape(fw["framework_title"] or "(untitled)")}</a><br>
      <code class="muted">{escape(fw["framework_id"])}</code></td>
  <td class="num">{fw["snapshot_count"]}</td>
  <td class="num">{_fmt(metrics.get("global_coherence"))}</td>
  <td class="num">{_fmt(metrics.get("fracture_density"))}</td>
  <td class="num">{_fmt(metrics.get("node_count"))}</td>
  <td class="muted">{escape(fw["latest_created_at"])}</td>
</tr>""")
        body = f"""
<h1>Frameworks <span class="muted">({len(rows)})</span></h1>
<p class="muted">Saved by <code>milcah metrics &lt;file&gt; --save</code>; each row is a
framework whose coherence is being tracked over time (FR10).</p>
<table>
<tr><th>Framework</th><th>Snapshots</th><th>Coherence</th><th>Fracture density</th><th>Nodes</th><th>Latest</th></tr>
{''.join(rows) or '<tr><td colspan="6" class="muted">(no snapshots saved yet)</td></tr>'}
</table>
"""
        return _base("Frameworks", body, store_label)

    @app.get("/frameworks/{framework_id}", response_class=HTMLResponse)
    def framework_detail(framework_id: str) -> str:
        snaps = _history_or_404(framework_id)
        trend = compute_trend(snaps)
        latest = snaps[-1]

        metric_rows = []
        for metric in TREND_METRICS:
            data = trend["metrics"][metric]
            values = data["values"]
            present = [v for v in values if isinstance(v, (int, float))]
            metric_rows.append(f"""
<tr>
  <td><code>{escape(metric)}</code></td>
  <td>{_sparkline(values)}</td>
  <td class="num">{_fmt(present[0] if present else None)}</td>
  <td class="num">{_fmt(present[-1] if present else None)}</td>
  <td>{_delta_cell(metric, data["delta"])}</td>
</tr>""")

        snap_rows = "".join(
            f"""
<tr>
  <td><a href="/frameworks/{escape(framework_id)}/snapshots/{escape(s.snapshot_id)}"><code>{escape(s.snapshot_id)}</code></a></td>
  <td class="muted">{escape(s.created_at)}</td>
  <td class="num">{_fmt(s.metrics.get("global_coherence"))}</td>
  <td class="num">{_fmt(s.metrics.get("fracture_density"))}</td>
  <td class="num">{_fmt(s.metrics.get("unresolved_load"))}</td>
  <td class="num">{len(s.units)}</td>
</tr>"""
            for s in reversed(snaps)
        )

        body = f"""
<h1>{escape(latest.framework_title or "(untitled)")}</h1>
<p><a href="/">&larr; all frameworks</a> ·
   <code>{escape(framework_id)}</code> ·
   {len(snaps)} snapshot(s)</p>
<h2>Trend</h2>
<p class="muted">First → last movement per metric; colour reads the direction
(green = improving, red = degrading under pressure).</p>
<table>
<tr><th>Metric</th><th>Series</th><th>First</th><th>Last</th><th>Δ</th></tr>
{''.join(metric_rows)}
</table>
<h2>Snapshots</h2>
<table>
<tr><th>Snapshot</th><th>Created</th><th>Coherence</th><th>Fracture density</th><th>Unresolved</th><th>Units</th></tr>
{snap_rows}
</table>
"""
        return _base(latest.framework_title or framework_id, body, store_label)

    @app.get("/frameworks/{framework_id}/snapshots/{snapshot_id}", response_class=HTMLResponse)
    def snapshot_detail(framework_id: str, snapshot_id: str) -> str:
        snap = store.load(framework_id, snapshot_id)
        if snap is None:
            raise HTTPException(404, f"snapshot not found: {snapshot_id}")

        metric_rows = "".join(
            f"<tr><th><code>{escape(str(k))}</code></th><td class='num'>{_fmt(v)}</td></tr>"
            for k, v in snap.metrics.items()
        )

        unit_types: dict[str, int] = {}
        for unit in snap.units:
            kind = str(unit.get("unit_type") or unit.get("type") or "unknown")
            unit_types[kind] = unit_types.get(kind, 0) + 1
        units_summary = (
            " · ".join(f"{escape(kind)}: {n}" for kind, n in sorted(unit_types.items()))
            or "(none)"
        )

        def _json_details(label: str, payload: Any) -> str:
            if not payload:
                return ""
            pretty = json.dumps(payload, indent=2, ensure_ascii=False)
            return (
                f"<details><summary>{escape(label)}</summary>"
                f"<pre>{escape(pretty)}</pre></details>"
            )

        body = f"""
<h1>Snapshot <code>{escape(snap.snapshot_id)}</code></h1>
<p><a href="/frameworks/{escape(framework_id)}">&larr; {escape(snap.framework_title or framework_id)}</a> ·
   <span class="muted">{escape(snap.created_at)}</span></p>
<h2>Metrics</h2>
<table class="kvbox">
{metric_rows or '<tr><td class="muted">(no metrics recorded)</td></tr>'}
</table>
<h2>Units <span class="muted">({len(snap.units)})</span></h2>
<p>{units_summary}</p>
<h2>Raw</h2>
{_json_details("framework", snap.framework)}
{_json_details("units", snap.units)}
{_json_details("ontology", snap.ontology)}
"""
        return _base(f"Snapshot {snap.snapshot_id[:8]}", body, store_label)

    return app
