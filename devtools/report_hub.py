#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified report hub (build/list/open)."""

from __future__ import annotations

import argparse
import http.server
import json
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine  # type: ignore
from devtools.report_utils import (
    file_info,
    now_iso,
    read_text,
    render_markdown,
    summarize_catalog_quality,
    summarize_quality_gate,
    summarize_static_mechanics,
    web_path,
)

try:
    from core.config import wagstaff_config  # type: ignore
except Exception:
    wagstaff_config = None  # type: ignore

REPORT_DIR = PROJECT_ROOT / "data" / "reports"
MANIFEST_PATH = REPORT_DIR / "wagstaff_report_manifest.json"
INDEX_PATH = REPORT_DIR / "index.html"


REPORT_SPECS = [
    {
        "id": "quality_gate",
        "title": "Quality Gate",
        "kind": "quality",
        "files": [
            {"path": "data/reports/quality_gate_report.md", "format": "md"},
            {"path": "data/reports/quality_gate_report.json", "format": "json"},
        ],
    },
    {
        "id": "catalog_quality",
        "title": "Catalog Quality",
        "kind": "quality",
        "files": [
            {"path": "data/reports/catalog_quality_report.md", "format": "md"},
            {"path": "data/reports/catalog_quality_report.json", "format": "json"},
        ],
    },
    {
        "id": "static_mechanics_coverage",
        "title": "Static Mechanics Coverage",
        "kind": "quality",
        "files": [
            {"path": "data/reports/static_mechanics_coverage_report.md", "format": "md"},
            {"path": "data/reports/static_mechanics_coverage_report.json", "format": "json"},
        ],
    },
    {
        "id": "stats_gap_inspect",
        "title": "Stats Gap Inspect",
        "kind": "quality",
        "optional": True,
        "files": [
            {"path": "data/reports/stats_gap_inspect.md", "format": "md"},
            {"path": "data/reports/stats_gap_inspect.json", "format": "json"},
        ],
    },
    {
        "id": "mechanism_summary",
        "title": "Mechanism Summary",
        "kind": "mechanism",
        "files": [{"path": "data/reports/mechanism_index_summary.md", "format": "md"}],
    },
    {
        "id": "mechanism_crosscheck",
        "title": "Mechanism Crosscheck",
        "kind": "mechanism",
        "files": [{"path": "data/reports/mechanism_crosscheck_report.md", "format": "md"}],
    },
    {
        "id": "raw_scan",
        "title": "DST Raw Coverage",
        "kind": "scan",
        "files": [
            {"path": "data/reports/dst_raw_coverage.md", "format": "md"},
            {"path": "data/reports/dst_raw_coverage.json", "format": "json"},
        ],
    },
    {
        "id": "asset_registry",
        "title": "Asset Registry",
        "kind": "scan",
        "files": [{"path": "data/reports/asset_registry.md", "format": "md"}],
    },
    {
        "id": "recipe_distribution",
        "title": "Recipe Distribution",
        "kind": "scan",
        "files": [{"path": "data/reports/recipe_distribution.md", "format": "md"}],
    },
]


def _rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def build_report_manifest() -> Dict[str, Any]:
    reports: List[Dict[str, Any]] = []
    missing = 0
    partial = 0

    for spec in REPORT_SPECS:
        files: List[Dict[str, Any]] = []
        status = "missing"
        updated = None
        any_exists = False
        all_exists = True
        optional = bool(spec.get("optional"))
        for f in spec.get("files") or []:
            path = (PROJECT_ROOT / f["path"]).resolve()
            info = file_info(path)
            info["path"] = _rel_path(path)
            info["format"] = f.get("format")
            info["web_path"] = web_path(path, REPORT_DIR)
            files.append(info)
            if info["exists"]:
                any_exists = True
                updated = max(updated or 0, info["mtime"] or 0)
            else:
                all_exists = False
        if any_exists and all_exists:
            status = "ok"
        elif any_exists:
            status = "partial"
        else:
            status = "missing"

        if optional and status == "missing":
            status = "skipped"
        else:
            if status == "missing":
                missing += 1
            if status == "partial":
                partial += 1

        summary: Dict[str, Any] = {}
        if spec["id"] == "quality_gate":
            summary = summarize_quality_gate(PROJECT_ROOT / "data/reports/quality_gate_report.json")
        elif spec["id"] == "catalog_quality":
            summary = summarize_catalog_quality(PROJECT_ROOT / "data/reports/catalog_quality_report.json")
        elif spec["id"] == "static_mechanics_coverage":
            summary = summarize_static_mechanics(PROJECT_ROOT / "data/reports/static_mechanics_coverage_report.json")

        reports.append(
            {
                "id": spec["id"],
                "title": spec.get("title"),
                "kind": spec.get("kind"),
                "status": status,
                "updated": updated,
                "files": files,
                "summary": summary,
            }
        )

    return {
        "meta": {"tool": "report_hub", "generated": now_iso()},
        "counts": {"reports": len(reports), "missing": missing, "partial": partial},
        "reports": reports,
    }


def render_index_html(manifest: Dict[str, Any]) -> str:
    report_items = []
    report_panels = []

    for rep in manifest.get("reports") or []:
        rep_id = str(rep.get("id") or rep.get("title") or "report")
        status = rep.get("status") or "missing"
        updated = rep.get("updated")
        if updated:
            updated_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated))
        else:
            updated_str = "-"

        files = []
        md_html = ""
        for f in rep.get("files") or []:
            name = Path(str(f.get("path"))).name
            if f.get("exists") and f.get("web_path"):
                files.append(f'<a href="{f["web_path"]}">{name}</a>')
            else:
                files.append(name)
            if not md_html and f.get("format") == "md" and f.get("exists"):
                md_path = PROJECT_ROOT / str(f.get("path") or "")
                md_html = render_markdown(read_text(md_path))

        if not md_html:
            md_html = "<p>No markdown report available.</p>"

        summary = rep.get("summary") or {}
        summary_parts = [f"{k}={v}" for k, v in summary.items() if v is not None]
        summary_html = ""
        if summary_parts:
            summary_html = f"<div class=\"summary\">{', '.join(summary_parts)}</div>"

        file_line = " · ".join(files) if files else "-"
        report_items.append(
            f"""
            <button class="report-item" data-report="{rep_id}">
              <div class="report-title">{rep.get("title")}</div>
              <div class="report-meta">
                <span class="pill status-{status}">{status}</span>
                <span class="meta-text">{updated_str}</span>
              </div>
              <div class="report-files">{file_line}</div>
              {summary_html}
            </button>
            """
        )

        report_panels.append(
            f"""
            <section class="report-panel" data-report="{rep_id}">
              <header class="panel-head">
                <div>
                  <div class="panel-title">{rep.get("title")}</div>
                  <div class="panel-sub">{file_line}</div>
                </div>
                <span class="pill status-{status}">{status}</span>
              </header>
              <div class="md">{md_html}</div>
            </section>
            """
        )

    counts = manifest.get("counts") or {}
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Wagstaff Reports</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&family=Newsreader:opsz,wght@8..72,400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f6f1e7;
      --panel: #fffaf2;
      --ink: #161f1e;
      --muted: #52615f;
      --accent: #c75f2b;
      --accent-2: #1f5a56;
      --line: rgba(31, 90, 86, 0.18);
      --shadow: 0 20px 40px rgba(16, 25, 24, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background: var(--bg);
      background-image:
        radial-gradient(circle at 10% 10%, rgba(199, 95, 43, 0.10), transparent 40%),
        radial-gradient(circle at 90% 20%, rgba(31, 90, 86, 0.12), transparent 42%),
        linear-gradient(120deg, rgba(255, 255, 255, 0.65), rgba(255, 255, 255, 0));
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background-image: linear-gradient(rgba(31, 90, 86, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(31, 90, 86, 0.05) 1px, transparent 1px);
      background-size: 22px 22px;
      pointer-events: none;
      z-index: 0;
    }}
    .shell {{
      position: relative;
      z-index: 1;
      padding: 28px clamp(18px, 4vw, 48px) 56px;
      max-width: 1280px;
      margin: 0 auto;
    }}
    .top {{
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 20px;
      animation: rise 0.7s ease-out both;
    }}
    h1 {{
      font-family: "Newsreader", serif;
      font-size: clamp(32px, 4vw, 48px);
      margin: 0 0 8px;
      letter-spacing: -0.02em;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .chip {{
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(31, 90, 86, 0.12);
      color: var(--accent-2);
      font-weight: 600;
      font-size: 0.85rem;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 270px minmax(0, 1fr);
      gap: 18px;
    }}
    .nav {{
      position: sticky;
      top: 16px;
      align-self: start;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 12px;
    }}
    .nav h2 {{
      font-family: "Newsreader", serif;
      font-size: 1.1rem;
      margin: 0;
    }}
    .report-item {{
      background: transparent;
      border: 1px solid rgba(31, 90, 86, 0.15);
      border-radius: 14px;
      padding: 10px 12px;
      text-align: left;
      display: grid;
      gap: 6px;
      cursor: pointer;
      transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
      font: inherit;
    }}
    .report-item:hover {{
      transform: translateY(-2px);
      border-color: rgba(31, 90, 86, 0.35);
      background: rgba(31, 90, 86, 0.06);
    }}
    .report-item.active {{
      border-color: var(--accent-2);
      box-shadow: 0 10px 24px rgba(31, 90, 86, 0.18);
      background: rgba(31, 90, 86, 0.08);
    }}
    .report-title {{
      font-weight: 600;
      font-size: 0.95rem;
    }}
    .report-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      font-size: 0.78rem;
      color: var(--muted);
    }}
    .report-files {{
      color: var(--muted);
      font-size: 0.78rem;
    }}
    .summary {{
      font-size: 0.75rem;
      color: var(--muted);
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
      border: 1px solid transparent;
    }}
    .status-ok {{ background: rgba(31, 90, 86, 0.18); color: var(--accent-2); border-color: rgba(31, 90, 86, 0.3); }}
    .status-partial {{ background: rgba(199, 95, 43, 0.2); color: var(--accent); border-color: rgba(199, 95, 43, 0.4); }}
    .status-missing {{ background: rgba(173, 55, 42, 0.16); color: #a3372a; border-color: rgba(173, 55, 42, 0.4); }}
    .status-skipped {{ background: rgba(80, 96, 97, 0.18); color: var(--muted); border-color: rgba(80, 96, 97, 0.3); }}
    .viewer {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px 22px;
      box-shadow: var(--shadow);
      min-height: 360px;
      animation: floatIn 0.9s ease-out both;
    }}
    .report-panel {{
      display: none;
    }}
    .report-panel.active {{
      display: block;
    }}
    .panel-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid rgba(31, 90, 86, 0.12);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }}
    .panel-title {{
      font-family: "Newsreader", serif;
      font-size: 1.6rem;
      margin: 0 0 4px;
    }}
    .panel-sub {{
      color: var(--muted);
      font-size: 0.85rem;
    }}
    .md {{
      font-size: 0.95rem;
      line-height: 1.5;
    }}
    .md h1, .md h2, .md h3, .md h4 {{
      font-family: "Newsreader", serif;
      margin: 1.5rem 0 0.6rem;
    }}
    .md h1 {{ font-size: 1.5rem; }}
    .md h2 {{ font-size: 1.2rem; }}
    .md h3 {{ font-size: 1.05rem; }}
    .md p {{ margin: 0 0 0.8rem; }}
    .md ul {{
      padding-left: 18px;
      margin: 0 0 0.9rem;
    }}
    .md li {{ margin-bottom: 0.35rem; }}
    .md code {{
      font-family: "IBM Plex Mono", monospace;
      background: rgba(31, 90, 86, 0.12);
      padding: 2px 5px;
      border-radius: 6px;
      font-size: 0.88em;
    }}
    .md pre {{
      background: #162321;
      color: #f4efe6;
      padding: 12px 14px;
      border-radius: 12px;
      overflow: auto;
      margin: 0 0 1rem;
      font-size: 0.85rem;
    }}
    .md pre code {{
      background: transparent;
      padding: 0;
      color: inherit;
    }}
    .md table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0 0 1rem;
      font-size: 0.9rem;
    }}
    .md th, .md td {{
      border: 1px solid rgba(31, 90, 86, 0.2);
      padding: 6px 8px;
      text-align: left;
    }}
    .md th {{
      background: rgba(31, 90, 86, 0.1);
      font-weight: 600;
    }}
    a {{
      color: var(--accent-2);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(14px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes floatIn {{
      from {{ opacity: 0; transform: translateY(12px) scale(0.98); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    @media (max-width: 980px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .nav {{ position: static; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="top">
      <div>
        <h1>Wagstaff Report Console</h1>
        <div class="meta">Generated: {manifest.get('meta', {}).get('generated')}</div>
      </div>
      <div class="chips">
        <span class="chip">Reports: {counts.get("reports", 0)}</span>
        <span class="chip">Missing: {counts.get("missing", 0)}</span>
        <span class="chip">Partial: {counts.get("partial", 0)}</span>
      </div>
    </header>
    <div class="layout">
      <aside class="nav">
        <h2>Report Index</h2>
        {''.join(report_items) if report_items else '<div class="meta">No reports found.</div>'}
      </aside>
      <main class="viewer">
        {''.join(report_panels) if report_panels else '<p>No report content available.</p>'}
      </main>
    </div>
  </div>
  <script>
    const items = Array.from(document.querySelectorAll('.report-item'));
    const panels = Array.from(document.querySelectorAll('.report-panel'));
    function activate(id) {{
      items.forEach((btn) => btn.classList.toggle('active', btn.dataset.report === id));
      panels.forEach((panel) => panel.classList.toggle('active', panel.dataset.report === id));
      if (id) {{ history.replaceState(null, '', '#' + id); }}
    }}
    if (items.length) {{
      const hash = window.location.hash ? window.location.hash.slice(1) : '';
      const initial = items.find((btn) => btn.dataset.report === hash) || items[0];
      activate(initial.dataset.report);
      items.forEach((btn) => {{
        btn.addEventListener('click', () => activate(btn.dataset.report));
      }});
    }}
  </script>
</body>
</html>
"""


def _resolve_dst_root(arg: Optional[str]) -> Optional[str]:
    if arg:
        return str(arg)
    if wagstaff_config is None:
        return None
    try:
        return wagstaff_config.get("PATHS", "DST_ROOT")
    except Exception:
        return None


def _run_tool(args: List[str]) -> bool:
    cmd = [sys.executable, str(PROJECT_ROOT / args[0])] + args[1:]
    return subprocess.run(cmd, check=False).returncode == 0


def _build_asset_registry(engine: WagstaffEngine, out_path: Path) -> None:
    import re
    from collections import Counter, defaultdict

    targets = {
        "STRINGS": re.compile(r"STRINGS\.[A-Z0-9_]+\s*="),
        "Prefabs": re.compile(r"\bPrefab\s*\("),
        "LootTables": re.compile(r"\bSetLoot\s*\(|\bSetChanceLoot\s*\("),
        "Brains": re.compile(r"require\s*[\(\"']brains/"),
        "Widgets": re.compile(r"require\s*[\(\"']widgets/"),
    }
    stats = defaultdict(Counter)
    lua_files = [f for f in engine.file_list if f.endswith(".lua")]

    for fname in lua_files:
        content = engine.read_file(fname)
        if not content:
            continue
        clean = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
        for cat, pattern in targets.items():
            matches = pattern.findall(clean)
            if matches:
                stats[cat][fname] += len(matches)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Wagstaff Asset Registry")
    lines.append("")
    lines.append("| Category | Total Definitions | Top File |")
    lines.append("|----------|-------------------|----------|")
    for cat, file_counts in stats.items():
        total = sum(file_counts.values())
        top_file = file_counts.most_common(1)[0][0] if file_counts else "-"
        lines.append(f"| {cat} | {total} | `{top_file}` |")
    lines.append("")
    lines.append("## Detailed Breakdown")
    for cat, file_counts in stats.items():
        lines.append("")
        lines.append(f"### {cat}")
        for fname, count in file_counts.most_common(10):
            lines.append(f"- `{fname}`: {count}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_recipe_distribution(engine: WagstaffEngine, out_path: Path) -> None:
    import re
    from collections import Counter, defaultdict

    pattern = re.compile(r"^\s*([a-zA-Z0-9_]*Recipe[a-zA-Z0-9_]*)\s*\(", re.MULTILINE)
    stats = Counter()
    file_stats = defaultdict(int)
    lua_files = [f for f in engine.file_list if f.endswith(".lua")]

    for fname in lua_files:
        content = engine.read_file(fname)
        if not content:
            continue
        clean = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
        matches = pattern.findall(clean)
        for m in matches:
            if "Get" in m or "Find" in m:
                continue
            stats[m] += 1
            file_stats[fname] += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Wagstaff Recipe Distribution")
    lines.append("")
    lines.append("## Function Usage")
    for func, count in stats.most_common():
        lines.append(f"- **{func}**: {count}")
    lines.append("")
    lines.append("## File Hotspots (Top 20)")
    for fname, count in sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
        lines.append(f"- `{fname}`: {count} recipes")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_reports(
    *, run_quality: bool, run_scan: bool, run_stats_gap: bool, dst_root: Optional[str]
) -> None:
    if run_quality:
        _run_tool(["devtools/quality_gate.py"])
        _run_tool(["devtools/catalog_quality.py"])
        _run_tool(["devtools/static_mechanics_coverage.py"])

    if run_scan:
        args = ["devtools/raw_scan.py"]
        if dst_root:
            args += ["--dst-root", dst_root]
        _run_tool(args)

        resolved = _resolve_dst_root(dst_root)
        if resolved:
            try:
                engine = WagstaffEngine(load_db=False, silent=True, dst_root=resolved)
            except Exception:
                return
            _build_asset_registry(engine, REPORT_DIR / "asset_registry.md")
            _build_recipe_distribution(engine, REPORT_DIR / "recipe_distribution.md")

    if run_stats_gap:
        _run_tool(["devtools/stats_gap_inspect.py"])


def write_manifest_and_index() -> Dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_report_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    INDEX_PATH.write_text(render_index_html(manifest), encoding="utf-8")
    return manifest


def _serve_reports(host: str, port: int, open_browser: bool) -> None:
    from functools import partial

    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(REPORT_DIR))
    httpd = http.server.ThreadingHTTPServer((host, port), handler)

    url_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{url_host}:{port}/index.html"
    print(f"Reports: {url}")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> int:
    p = argparse.ArgumentParser(description="Report hub (build/list/open).")
    sub = p.add_subparsers(dest="cmd")

    p_build = sub.add_parser("build", help="Build reports and refresh manifest")
    p_build.add_argument("--all", action="store_true", help="Run quality + scan reports")
    p_build.add_argument("--quality", action="store_true", help="Run quality reports")
    p_build.add_argument("--scan", action="store_true", help="Run scan reports")
    p_build.add_argument("--stats-gap", action="store_true", help="Run stats gap inspection report")
    p_build.add_argument("--dst-root", default=None, help="Override DST root")

    p_list = sub.add_parser("list", help="List report status")

    p_open = sub.add_parser("open", help="Serve reports in a local browser")
    p_open.add_argument("--host", default="127.0.0.1")
    p_open.add_argument("--port", type=int, default=18000)
    p_open.add_argument("--no-open", action="store_true", help="Do not open browser")

    args = p.parse_args()
    cmd = args.cmd or "list"

    if cmd == "build":
        run_quality = bool(args.all or args.quality)
        run_scan = bool(args.all or args.scan)
        run_stats_gap = bool(args.stats_gap)
        build_reports(
            run_quality=run_quality,
            run_scan=run_scan,
            run_stats_gap=run_stats_gap,
            dst_root=args.dst_root,
        )
        manifest = write_manifest_and_index()
        print(f"OK: Report manifest written: {MANIFEST_PATH}")
        print(f"OK: Report index written: {INDEX_PATH}")
        print(f"Reports: {manifest.get('counts')}")
        return 0

    if cmd == "open":
        write_manifest_and_index()
        _serve_reports(args.host, int(args.port), not bool(args.no_open))
        return 0

    manifest = write_manifest_and_index()
    counts = manifest.get("counts") or {}
    print(f"Reports total={counts.get('reports')} missing={counts.get('missing')} partial={counts.get('partial')}")
    for rep in manifest.get("reports") or []:
        print(f"- {rep.get('title')}: {rep.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
