#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Portal hub: aggregate mgmt + quality + report + index status for CLI/web."""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.cli.mgmt_parser import parse_milestones  # noqa: E402
from devtools import report_hub  # noqa: E402
from devtools.report_utils import (  # noqa: E402
    load_json,
    now_iso,
    read_text,
    render_markdown,
    summarize_index_manifest,
    summarize_quality_gate,
)

REPORT_DIR = PROJECT_ROOT / "data" / "reports"
PORTAL_MANIFEST_PATH = REPORT_DIR / "wagstaff_portal_manifest.json"
PORTAL_INDEX_PATH = REPORT_DIR / "portal_index.html"


def build_portal_manifest() -> Dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_manifest = report_hub.write_manifest_and_index()

    status_path = PROJECT_ROOT / "PROJECT_STATUS.json"
    status_doc = load_json(status_path)
    mgmt_doc_path = status_doc.get("MANAGEMENT_DOC")
    mgmt_doc_path = str(mgmt_doc_path) if isinstance(mgmt_doc_path, str) else "docs/management/PROJECT_MANAGEMENT.md"
    mgmt_text = read_text(PROJECT_ROOT / mgmt_doc_path)

    milestones = parse_milestones(mgmt_text)
    quality_summary = summarize_quality_gate(PROJECT_ROOT / "data/reports/quality_gate_report.json")
    index_summary = summarize_index_manifest(PROJECT_ROOT / "data/index/wagstaff_index_manifest.json")

    reports: List[Dict[str, Any]] = []
    for rep in report_manifest.get("reports") or []:
        files = []
        md_path = None
        for f in rep.get("files") or []:
            path = Path(str(f.get("path") or ""))
            files.append(
                {
                    "path": str(path),
                    "format": f.get("format"),
                    "exists": bool(f.get("exists")),
                    "web_path": f.get("web_path"),
                }
            )
            if not md_path and f.get("format") == "md" and f.get("exists"):
                md_path = str(path)
        reports.append(
            {
                "id": rep.get("id"),
                "title": rep.get("title"),
                "status": rep.get("status"),
                "updated": rep.get("updated"),
                "files": files,
                "summary": rep.get("summary") or {},
                "md_path": md_path,
            }
        )

    return {
        "meta": {"tool": "portal_hub", "generated": now_iso()},
        "project": {
            "objective": status_doc.get("OBJECTIVE") or "-",
            "tasks_todo": status_doc.get("TASKS_TODO") or [],
            "tasks_done": status_doc.get("TASKS_DONE") or [],
            "recent_logs": status_doc.get("RECENT_LOGS") or [],
            "management_doc": mgmt_doc_path,
        },
        "milestones": [m.__dict__ for m in milestones],
        "quality": quality_summary,
        "reports": {
            "counts": report_manifest.get("counts") or {},
            "items": reports,
            "index_path": "data/reports/index.html",
        },
        "index_manifest": index_summary,
    }


def render_portal_html(doc: Dict[str, Any]) -> str:
    project = doc.get("project") or {}
    tasks_todo = project.get("tasks_todo") or []
    tasks_done = project.get("tasks_done") or []
    recent_logs = project.get("recent_logs") or []
    milestones = doc.get("milestones") or []
    quality = doc.get("quality") or {}
    reports = doc.get("reports") or {}
    report_items = reports.get("items") or []
    index_summary = doc.get("index_manifest") or {}

    def _status_class(status: str) -> str:
        if status in ("ok", "done"):
            return "ok"
        if status in ("partial", "in_progress"):
            return "warn"
        if status in ("missing", "failed", "fail"):
            return "bad"
        return "muted"

    report_tabs = []
    report_panels = []
    for rep in report_items:
        rep_id = str(rep.get("id") or rep.get("title") or "report")
        status = rep.get("status") or "missing"
        updated = rep.get("updated")
        updated_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(updated)) if updated else "-"
        files = []
        for f in rep.get("files") or []:
            name = Path(str(f.get("path"))).name
            if f.get("exists") and f.get("web_path"):
                files.append(f'<a href="{f["web_path"]}">{name}</a>')
            else:
                files.append(name)
        file_line = " · ".join(files) if files else "-"
        summary = rep.get("summary") or {}
        summary_parts = [f"{k}={v}" for k, v in summary.items() if v is not None]
        summary_line = f"<div class=\"summary\">{', '.join(summary_parts)}</div>" if summary_parts else ""
        report_tabs.append(
            f"""
            <button class="report-tab" data-report="{rep_id}">
              <div class="tab-title">{rep.get("title")}</div>
              <div class="tab-meta">
                <span class="pill pill-{_status_class(status)}">{status}</span>
                <span class="tab-date">{updated_str}</span>
              </div>
              <div class="tab-files">{file_line}</div>
              {summary_line}
            </button>
            """
        )
        md_path = rep.get("md_path")
        if md_path:
            md_html = render_markdown(read_text(PROJECT_ROOT / md_path))
            if not md_html.strip():
                md_html = "<p>No markdown report available.</p>"
        else:
            md_html = "<p>No markdown report available.</p>"
        report_panels.append(
            f"""
            <article class="report-panel" data-report="{rep_id}">
              <header class="report-head">
                <div>
                  <h3>{rep.get("title")}</h3>
                  <div class="report-sub">{file_line}</div>
                </div>
                <span class="pill pill-{_status_class(status)}">{status}</span>
              </header>
              <div class="md">{md_html}</div>
            </article>
            """
        )

    milestone_cards = []
    for m in milestones:
        status = m.get("status") or "unknown"
        milestone_cards.append(
            f"""
            <div class="mini-card">
              <div class="mini-title">{m.get("key")}</div>
              <div class="mini-body">{m.get("title")}</div>
              <span class="pill pill-{_status_class(status)}">{status}</span>
            </div>
            """
        )

    todo_lines = [f"<li>{row}</li>" for row in tasks_todo]
    done_lines = [f"<li>{row}</li>" for row in tasks_done]
    log_lines = [f"<li>{line}</li>" for line in list(recent_logs)[-8:]]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Wagstaff Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&family=Newsreader:opsz,wght@8..72,400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f7f2ea;
      --panel: #fffaf2;
      --ink: #18211f;
      --muted: #4f5f5d;
      --accent: #c75f2b;
      --accent-2: #1f5a56;
      --line: rgba(31, 90, 86, 0.18);
      --shadow: 0 18px 36px rgba(18, 28, 26, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background: var(--bg);
      background-image:
        radial-gradient(circle at 15% 10%, rgba(199, 95, 43, 0.10), transparent 45%),
        radial-gradient(circle at 85% 20%, rgba(31, 90, 86, 0.12), transparent 42%),
        linear-gradient(120deg, rgba(255, 255, 255, 0.7), rgba(255, 255, 255, 0));
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background-image: linear-gradient(rgba(31, 90, 86, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(31, 90, 86, 0.05) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
      z-index: 0;
    }}
    .shell {{
      position: relative;
      z-index: 1;
      padding: 28px clamp(18px, 4vw, 48px) 52px;
      max-width: 1400px;
      margin: 0 auto;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 20px;
      animation: rise 0.7s ease-out both;
    }}
    h1 {{
      font-family: "Newsreader", serif;
      font-size: clamp(32px, 4vw, 52px);
      margin: 0 0 8px;
      letter-spacing: -0.02em;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .stat-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .stat {{
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(31, 90, 86, 0.12);
      color: var(--accent-2);
      font-weight: 600;
      font-size: 0.85rem;
    }}
    .workspace {{
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 260px;
      gap: 18px;
    }}
    .rail {{
      display: grid;
      gap: 14px;
      align-self: start;
      position: sticky;
      top: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      box-shadow: var(--shadow);
      animation: floatIn 0.9s ease-out both;
    }}
    .panel h2 {{
      font-family: "Newsreader", serif;
      font-size: 1.15rem;
      margin: 0 0 10px;
    }}
    .panel h3 {{
      margin: 0 0 6px;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    .objective {{
      font-size: 0.95rem;
      color: var(--muted);
      line-height: 1.5;
      margin-bottom: 10px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .kpi {{
      padding: 10px;
      border-radius: 12px;
      background: rgba(31, 90, 86, 0.08);
    }}
    .kpi strong {{
      display: block;
      font-size: 1.05rem;
    }}
    .kpi span {{
      color: var(--muted);
      font-size: 0.82rem;
    }}
    .mini-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
    }}
    .mini-card {{
      padding: 10px;
      border-radius: 12px;
      border: 1px solid rgba(31, 90, 86, 0.12);
      background: rgba(255, 255, 255, 0.6);
      display: grid;
      gap: 6px;
    }}
    .mini-title {{
      font-weight: 600;
      color: var(--accent-2);
      font-size: 0.85rem;
    }}
    .mini-body {{
      font-size: 0.9rem;
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
    .pill-ok {{ background: rgba(31, 90, 86, 0.18); color: var(--accent-2); border-color: rgba(31, 90, 86, 0.3); }}
    .pill-warn {{ background: rgba(199, 95, 43, 0.2); color: var(--accent); border-color: rgba(199, 95, 43, 0.4); }}
    .pill-bad {{ background: rgba(173, 55, 42, 0.18); color: #a3372a; border-color: rgba(173, 55, 42, 0.4); }}
    .pill-muted {{ background: rgba(80, 96, 97, 0.14); color: var(--muted); border-color: rgba(80, 96, 97, 0.2); }}
    .tasks {{
      display: grid;
      gap: 10px;
    }}
    .task-cols {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .task-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.4;
    }}
    .logs {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.5;
    }}
    .report-board {{
      display: grid;
      gap: 12px;
    }}
    .report-tabs {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }}
    .report-tab {{
      border: 1px solid rgba(31, 90, 86, 0.18);
      border-radius: 14px;
      padding: 10px 12px;
      background: transparent;
      text-align: left;
      font: inherit;
      cursor: pointer;
      display: grid;
      gap: 6px;
      transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
    }}
    .report-tab:hover {{
      transform: translateY(-2px);
      border-color: rgba(31, 90, 86, 0.35);
      background: rgba(31, 90, 86, 0.06);
    }}
    .report-tab.active {{
      border-color: var(--accent-2);
      background: rgba(31, 90, 86, 0.08);
      box-shadow: 0 12px 26px rgba(31, 90, 86, 0.18);
    }}
    .tab-title {{
      font-weight: 600;
      font-size: 0.95rem;
    }}
    .tab-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 0.75rem;
    }}
    .tab-files {{
      color: var(--muted);
      font-size: 0.75rem;
    }}
    .summary {{
      font-size: 0.72rem;
      color: var(--muted);
    }}
    .report-view {{
      border-top: 1px solid rgba(31, 90, 86, 0.12);
      padding-top: 14px;
      max-height: 70vh;
      overflow: auto;
    }}
    .report-panel {{
      display: none;
    }}
    .report-panel.active {{
      display: block;
    }}
    .report-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid rgba(31, 90, 86, 0.12);
      padding-bottom: 10px;
      margin-bottom: 12px;
    }}
    .report-head h3 {{
      font-family: "Newsreader", serif;
      font-size: 1.4rem;
      margin: 0 0 4px;
    }}
    .report-sub {{
      color: var(--muted);
      font-size: 0.85rem;
    }}
    .md {{
      font-size: 0.94rem;
      line-height: 1.5;
    }}
    .md h1, .md h2, .md h3, .md h4 {{
      font-family: "Newsreader", serif;
      margin: 1.4rem 0 0.6rem;
    }}
    .md h1 {{ font-size: 1.4rem; }}
    .md h2 {{ font-size: 1.15rem; }}
    .md h3 {{ font-size: 1.0rem; }}
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
      font-size: 0.84rem;
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
    .link-grid {{
      display: grid;
      gap: 8px;
    }}
    .link-pill {{
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(31, 90, 86, 0.3);
      text-decoration: none;
      color: var(--accent-2);
      font-weight: 600;
      font-size: 0.85rem;
      transition: transform 0.2s ease, background 0.2s ease;
    }}
    .link-pill:hover {{
      transform: translateY(-2px);
      background: rgba(31, 90, 86, 0.08);
    }}
    a {{
      color: var(--accent-2);
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(16px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes floatIn {{
      from {{ opacity: 0; transform: translateY(12px) scale(0.98); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    @media (max-width: 1120px) {{
      .workspace {{ grid-template-columns: 1fr; }}
      .rail {{ position: static; }}
      .report-view {{ max-height: none; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Wagstaff Portal</h1>
        <div class="meta">Generated: {doc.get("meta", {}).get("generated")} · Mgmt doc: {project.get("management_doc")}</div>
      </div>
      <div class="stat-row">
        <div class="stat">Reports: {reports.get("counts", {}).get("reports", 0)}</div>
        <div class="stat">Missing: {reports.get("counts", {}).get("missing", 0)}</div>
        <div class="stat">Quality Fail: {quality.get("issues_fail", 0)}</div>
        <div class="stat">Quality Warn: {quality.get("issues_warn", 0)}</div>
      </div>
    </header>

    <div class="workspace">
      <aside class="rail">
        <section class="panel">
          <h2>Project Focus</h2>
          <div class="objective">{project.get("objective")}</div>
          <div class="kpis">
            <div class="kpi">
              <strong>{len(tasks_todo)}</strong>
              <span>Active Tasks</span>
            </div>
            <div class="kpi">
              <strong>{len(tasks_done)}</strong>
              <span>Completed Tasks</span>
            </div>
          </div>
        </section>
        <section class="panel">
          <h2>Milestones</h2>
          <div class="mini-grid">
            {''.join(milestone_cards) if milestone_cards else '<div class="mini-card">No milestones parsed.</div>'}
          </div>
        </section>
        <section class="panel tasks">
          <h2>Tasks</h2>
          <div class="task-cols">
            <div>
              <h3>Active</h3>
              <ul class="task-list">
                {''.join(todo_lines) if todo_lines else '<li>No active tasks.</li>'}
              </ul>
            </div>
            <div>
              <h3>Done</h3>
              <ul class="task-list">
                {''.join(done_lines) if done_lines else '<li>No completed tasks.</li>'}
              </ul>
            </div>
          </div>
        </section>
        <section class="panel">
          <h2>Recent Logs</h2>
          <ul class="logs">
            {''.join(log_lines) if log_lines else '<li>No recent logs.</li>'}
          </ul>
        </section>
      </aside>

      <main class="panel report-board">
        <div>
          <h2>Reports</h2>
          <div class="meta">Inventory + direct markdown rendering</div>
        </div>
        <div class="report-tabs">
          {''.join(report_tabs) if report_tabs else '<div class="meta">No reports found.</div>'}
        </div>
        <div class="report-view">
          {''.join(report_panels) if report_panels else '<p>No report content available.</p>'}
        </div>
      </main>

      <aside class="rail">
        <section class="panel">
          <h2>Quality Pulse</h2>
          <div class="kpis">
            <div class="kpi">
              <strong>{quality.get("issues_total", 0)}</strong>
              <span>Total Issues</span>
            </div>
            <div class="kpi">
              <strong>{quality.get("catalog_items_total") or "-"}</strong>
              <span>Catalog Items</span>
            </div>
            <div class="kpi">
              <strong>{quality.get("mechanism_prefabs_total") or "-"}</strong>
              <span>Mechanism Prefabs</span>
            </div>
            <div class="kpi">
              <strong>{index_summary.get("artifacts_missing", 0)}</strong>
              <span>Missing Artifacts</span>
            </div>
          </div>
        </section>
        <section class="panel">
          <h2>Index Manifest</h2>
          <div class="kpis">
            <div class="kpi">
              <strong>{index_summary.get("artifacts_total", 0)}</strong>
              <span>Artifacts</span>
            </div>
            <div class="kpi">
              <strong>{index_summary.get("warnings", 0)}</strong>
              <span>Manifest Warnings</span>
            </div>
          </div>
        </section>
        <section class="panel">
          <h2>Quick Links</h2>
          <div class="link-grid">
            <a class="link-pill" href="{reports.get('index_path') or 'index.html'}">Report Hub</a>
            <a class="link-pill" href="quality_gate_report.md">Quality Gate</a>
            <a class="link-pill" href="catalog_quality_report.md">Catalog Quality</a>
            <a class="link-pill" href="../index/wagstaff_index_manifest.json">Index Manifest</a>
          </div>
        </section>
      </aside>
    </div>
  </div>
  <script>
    const tabs = Array.from(document.querySelectorAll('.report-tab'));
    const panels = Array.from(document.querySelectorAll('.report-panel'));
    function activate(id) {{
      tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.report === id));
      panels.forEach((panel) => panel.classList.toggle('active', panel.dataset.report === id));
      if (id) {{ history.replaceState(null, '', '#' + id); }}
    }}
    if (tabs.length) {{
      const hash = window.location.hash ? window.location.hash.slice(1) : '';
      const initial = tabs.find((tab) => tab.dataset.report === hash) || tabs[0];
      activate(initial.dataset.report);
      tabs.forEach((tab) => tab.addEventListener('click', () => activate(tab.dataset.report)));
    }}
  </script>
</body>
</html>
"""


def write_portal_artifacts() -> Dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_portal_manifest()
    PORTAL_MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    PORTAL_INDEX_PATH.write_text(render_portal_html(manifest), encoding="utf-8")
    return manifest


def _serve_portal(host: str, port: int, open_browser: bool) -> None:
    from functools import partial

    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(REPORT_DIR))
    httpd = http.server.ThreadingHTTPServer((host, port), handler)

    url_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{url_host}:{port}/portal_index.html"
    print(f"Portal: {url}")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> int:
    p = argparse.ArgumentParser(description="Portal hub (build/list/open).")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("build", help="Build portal manifest + HTML")
    sub.add_parser("list", help="List portal summary")

    p_open = sub.add_parser("open", help="Open portal in a local browser")
    p_open.add_argument("--host", default="127.0.0.1")
    p_open.add_argument("--port", type=int, default=19000)
    p_open.add_argument("--no-open", action="store_true", help="Do not open browser")

    args = p.parse_args()
    cmd = args.cmd or "list"

    if cmd == "build":
        manifest = write_portal_artifacts()
        print(f"OK: Portal manifest written: {PORTAL_MANIFEST_PATH}")
        print(f"OK: Portal index written: {PORTAL_INDEX_PATH}")
        print(f"Portal: reports={manifest.get('reports', {}).get('counts', {})}")
        return 0

    if cmd == "open":
        write_portal_artifacts()
        _serve_portal(args.host, int(args.port), not bool(args.no_open))
        return 0

    manifest = write_portal_artifacts()
    reports = manifest.get("reports", {}).get("counts", {})
    quality = manifest.get("quality", {})
    print(
        f"Portal: reports={reports} quality_fail={quality.get('issues_fail', 0)} quality_warn={quality.get('issues_warn', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
