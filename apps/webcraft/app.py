# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .catalog_store import CatalogStore
from .icon_service import IconConfig, IconService
from .i18n_index import I18nIndexStore
from .settings import WebCraftSettings
from .tuning_trace import TuningTraceStore
from .ui import render_index_html, render_cooking_html, render_catalog_html


def create_app(
    catalog_path: Path,
    *,
    root_path: str = "",
    cors_allow_origins: Optional[Sequence[str]] = None,
    gzip_minimum_size: int = 800,
    auto_reload_catalog: bool = False,
    # icons
    icons_mode: str = "auto",
    game_data_dir: Optional[Path] = None,
    icons_unpremultiply: bool = True,
    static_root_dir: Optional[Path] = None,
    # analyzer (optional)
    enable_analyzer: bool = False,
    analyzer_load_db: bool = False,
    dst_root: Optional[Path] = None,
    scripts_zip: Optional[Path] = None,
    scripts_dir: Optional[Path] = None,
    # tuning trace (optional)
    tuning_trace_path: Optional[Path] = None,
    auto_reload_tuning_trace: bool = False,
    # i18n index (optional)
    i18n_index_path: Optional[Path] = None,
    auto_reload_i18n_index: bool = False,
) -> FastAPI:
    """FastAPI app factory."""

    rp = WebCraftSettings.normalize_root_path(root_path)

    app = FastAPI(
        title="Wagstaff WebCraft API",
        version="1.0",
        root_path=rp,
        docs_url="/docs",
        redoc_url=None,
    )

    # static: app assets vs data outputs
    project_root = Path(__file__).resolve().parents[2]
    app_static_root = project_root / "apps" / "webcraft" / "static"
    data_static_root = Path(static_root_dir) if static_root_dir else (project_root / "data" / "static")
    try:
        app_static_root.mkdir(parents=True, exist_ok=True)
        data_static_root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    app.mount("/static/app", StaticFiles(directory=str(app_static_root), check_dir=False), name="static-app")
    app.mount("/static/data", StaticFiles(directory=str(data_static_root), check_dir=False), name="static-data")

    # state
    app.state.store = CatalogStore(Path(catalog_path))

    # tuning trace (separate from catalog)
    ttp = Path(tuning_trace_path) if tuning_trace_path else (Path(catalog_path).parent / "wagstaff_tuning_trace_v1.json")
    app.state.tuning_trace_path = ttp
    if ttp.exists():
        app.state.tuning_trace_store = TuningTraceStore(ttp)
    else:
        app.state.tuning_trace_store = None
    app.state.auto_reload_tuning_trace = bool(auto_reload_tuning_trace or auto_reload_catalog)

    # i18n index (separate from catalog)
    iip = Path(i18n_index_path) if i18n_index_path else (Path(catalog_path).parent / "wagstaff_i18n_v1.json")
    app.state.i18n_index_path = iip
    if iip.exists():
        app.state.i18n_index_store = I18nIndexStore(iip)
    else:
        app.state.i18n_index_store = None
    app.state.auto_reload_i18n_index = bool(auto_reload_i18n_index or auto_reload_catalog)

    # analyzer (auto-on if scripts_zip hint is available)
    scripts_zip_hint = None
    scripts_dir_hint = None
    try:
        scripts_zip_hint = str((app.state.store.meta() or {}).get("scripts_zip") or "").strip() or None
    except Exception:
        scripts_zip_hint = None
    try:
        scripts_dir_hint = str((app.state.store.meta() or {}).get("scripts_dir") or "").strip() or None
    except Exception:
        scripts_dir_hint = None

    scripts_zip_arg = scripts_zip
    scripts_dir_arg = scripts_dir
    dst_root_arg = dst_root
    enable_analyzer_arg = bool(enable_analyzer)

    if (not enable_analyzer_arg) and (not dst_root_arg) and (not scripts_zip_arg) and (not scripts_dir_arg):
        if scripts_zip_hint and Path(scripts_zip_hint).exists():
            scripts_zip_arg = Path(scripts_zip_hint)
            enable_analyzer_arg = True
        elif scripts_dir_hint and Path(scripts_dir_hint).exists():
            scripts_dir_arg = Path(scripts_dir_hint)
            enable_analyzer_arg = True

    # optional live analyzer (mount scripts source for on-demand parsing)
    app.state.engine = None
    if enable_analyzer_arg or dst_root_arg or scripts_zip_arg or scripts_dir_arg:
        try:
            from core.engine import WagstaffEngine
            app.state.engine = WagstaffEngine(
                load_db=bool(analyzer_load_db),
                silent=True,
                dst_root=str(dst_root_arg) if dst_root_arg else None,
                scripts_zip=str(scripts_zip_arg) if scripts_zip_arg else None,
                scripts_dir=str(scripts_dir_arg) if scripts_dir_arg else None,
            )
        except Exception:
            app.state.engine = None
    app.state.auto_reload_catalog = bool(auto_reload_catalog)

    # i18n index only (runtime PO parsing disabled)
    app.state.i18n_service = None

    icons_dir = data_static_root / "icons"
    try:
        icons_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    cfg = IconConfig(
        mode=str(icons_mode or "auto"),
        static_dir=icons_dir,
        game_data_dir=(Path(game_data_dir).expanduser().resolve() if game_data_dir else None),
        unpremultiply=bool(icons_unpremultiply),
    )
    app.state.icon_service = IconService(cfg)

    # middleware
    if gzip_minimum_size and gzip_minimum_size > 0:
        app.add_middleware(GZipMiddleware, minimum_size=int(gzip_minimum_size))

    if cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_allow_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # routes
    app.include_router(api_router)

    @app.on_event("shutdown")
    def _shutdown() -> None:
        eng = getattr(app.state, "engine", None)
        if eng is not None:
            try:
                eng.close()
            except Exception:
                pass

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        # root_path is already applied by FastAPI; still need it for frontend URL prefixing
        root = request.scope.get("root_path") or ""
        return HTMLResponse(render_index_html(app_root=str(root)))

    @app.get("/cooking", response_class=HTMLResponse)
    def cooking(request: Request):
        root = request.scope.get("root_path") or ""
        return HTMLResponse(render_cooking_html(app_root=str(root)))


    @app.get("/catalog", response_class=HTMLResponse)
    def catalog(request: Request):
        root = request.scope.get("root_path") or ""
        return HTMLResponse(render_catalog_html(app_root=str(root)))

    return app
