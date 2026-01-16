#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run WebCraft server (FastAPI + Uvicorn).

Usage:
  python3 devtools/serve_webcraft.py --host 0.0.0.0 --port 20000 --no-open
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for p in (PROJECT_ROOT / "core", PROJECT_ROOT / "apps"):
    if str(p) not in sys.path:
        sys.path.append(str(p))

import uvicorn  # type: ignore

from webcraft.app import create_app  # type: ignore


def _detect_lan_ip() -> str:
    """Best-effort LAN IP discovery (no external network required)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # doesn't need to be reachable; used to pick outbound interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Wagstaff WebCraft (FastAPI) server.")
    parser.add_argument("--catalog", default=str(PROJECT_ROOT / "data" / "index" / "wagstaff_catalog_v2.json"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--root-path", default="", help="Reverse proxy mount path, e.g. /webcraft")
    parser.add_argument("--reload", action="store_true", help="Auto-reload code (development)")
    parser.add_argument("--reload-catalog", action="store_true", help="Auto-reload catalog when file changes")
    parser.add_argument("--reload-trace", action="store_true", help="Auto-reload tuning trace file when it changes")
    parser.add_argument("--reload-i18n", action="store_true", help="Auto-reload i18n index when it changes")
    parser.add_argument("--no-open", action="store_true", help="Do not open browser")
    parser.add_argument("--log-level", default="info", choices=["critical","error","warning","info","debug","trace"])
    parser.add_argument("--cors-allow-origin", action="append", default=[], help="CORS allow origin (repeatable)")
    # icons
    parser.add_argument(
        "--icons",
        default=os.environ.get("WAGSTAFF_ICONS_MODE", "auto"),
        choices=["off", "static", "dynamic", "auto"],
        help="Icon mode: off|static (png)|dynamic (tex)|auto",
    )
    parser.add_argument(
        "--game-data",
        default=os.environ.get("WAGSTAFF_GAME_DATA", ""),
        help="DST data root (must contain images/... for dynamic icons)",
    )
    parser.add_argument(
        "--icons-straight-alpha",
        action="store_true",
        help="Do not unpremultiply alpha when cropping icons (advanced)",
    )
    parser.add_argument(
        "--tuning-trace",
        default=os.environ.get("WAGSTAFF_TUNING_TRACE", ""),
        help="Optional tuning trace JSON path (default: catalog dir/wagstaff_tuning_trace_v1.json)",
    )
    parser.add_argument(
        "--i18n-index",
        default=os.environ.get("WAGSTAFF_I18N_INDEX", ""),
        help="Optional i18n index JSON path (default: catalog dir/wagstaff_i18n_v1.json)",
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog).expanduser().resolve()
    if not catalog_path.exists():
        print(f"❌ Catalog not found: {catalog_path}")
        sys.exit(2)

    app = create_app(
        catalog_path=catalog_path,
        root_path=args.root_path,
        cors_allow_origins=(args.cors_allow_origin or None),
        gzip_minimum_size=800,
        auto_reload_catalog=bool(args.reload_catalog),
        icons_mode=str(args.icons),
        game_data_dir=(Path(args.game_data).expanduser().resolve() if args.game_data else None),
        icons_unpremultiply=(not bool(args.icons_straight_alpha)),
        tuning_trace_path=(Path(args.tuning_trace).expanduser().resolve() if args.tuning_trace else None),
        auto_reload_tuning_trace=bool(args.reload_trace or args.reload_catalog),
        i18n_index_path=(Path(args.i18n_index).expanduser().resolve() if args.i18n_index else None),
        auto_reload_i18n_index=bool(args.reload_i18n or args.reload_catalog),
    )

    host = str(args.host)
    port = int(args.port)

    # Print useful addresses
    rp = (args.root_path or "").rstrip("/")
    local_url = f"http://127.0.0.1:{port}{rp}/"
    if host == "0.0.0.0":
        lan_ip = _detect_lan_ip()
        lan_url = f"http://{lan_ip}:{port}{rp}/"
        print(f"Wagstaff WebCraft: {lan_url}")
        print(f"Open (local): {local_url}")
        print(f"Catalog: {catalog_path}")
        open_url = lan_url
    else:
        url = f"http://{host}:{port}{rp}/"
        print(f"Wagstaff WebCraft: {url}")
        print(f"Catalog: {catalog_path}")
        open_url = url

    if not args.no_open:
        try:
            webbrowser.open(open_url)
        except Exception:
            pass

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=args.log_level,
        reload=bool(args.reload),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
