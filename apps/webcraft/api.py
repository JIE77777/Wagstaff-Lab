# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

import hashlib

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .catalog_store import CatalogStore, CraftRecipe, CookingRecipe
from .planner import craftable_recipes, missing_for, normalize_inventory
from .cooking_planner import explore_cookpot, find_cookable, simulate_cookpot, normalize_counts


def get_store(request: Request) -> CatalogStore:
    """Resolve the catalog store from app state (with optional auto-reload)."""

    store: CatalogStore = request.app.state.store  # type: ignore[attr-defined]
    auto = bool(getattr(request.app.state, "auto_reload_catalog", False))
    if auto:
        try:
            store.load(force=False)
        except Exception:
            # do not break requests on reload errors
            pass
    return store


def _cache_headers(request: Request, *, max_age: int, etag: Optional[str] = None) -> Dict[str, str]:
    if max_age <= 0:
        return {}
    if bool(getattr(request.app.state, "auto_reload_catalog", False)):
        return {}
    headers = {"Cache-Control": f"public, max-age={int(max_age)}"}
    if etag:
        headers["ETag"] = str(etag)
    return headers


def _json(data: Dict[str, Any], *, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    return JSONResponse(content=data, headers=headers or {})


router = APIRouter(prefix="/api/v1")


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


# ----------------- optional tuning traces (requires analyzer engine) -----------------


def _get_engine(request: Request):
    return getattr(request.app.state, "engine", None)


def _get_tuning_trace_store(request: Request):
    store = getattr(request.app.state, "tuning_trace_store", None)
    if store is None:
        path = getattr(request.app.state, "tuning_trace_path", None)
        if path:
            try:
                from pathlib import Path
                from .tuning_trace import TuningTraceStore

                p = Path(path)
                if p.exists():
                    store = TuningTraceStore(p)
                    request.app.state.tuning_trace_store = store
            except Exception:
                store = None
    auto = bool(getattr(request.app.state, "auto_reload_tuning_trace", False))
    if store is not None and auto:
        try:
            store.load(force=False)
        except Exception:
            pass
    return store


def _get_i18n_index_store(request: Request):
    store = getattr(request.app.state, "i18n_index_store", None)
    if store is None:
        path = getattr(request.app.state, "i18n_index_path", None)
        if path:
            try:
                from pathlib import Path
                from .i18n_index import I18nIndexStore

                p = Path(path)
                if p.exists():
                    store = I18nIndexStore(p)
                    request.app.state.i18n_index_store = store
            except Exception:
                store = None
    auto = bool(getattr(request.app.state, "auto_reload_i18n_index", False))
    if store is not None and auto:
        try:
            store.load(force=False)
        except Exception:
            pass
    return store


def _ensure_tuning(engine, store_meta: Optional[Dict[str, Any]] = None) -> Any:
    """Best-effort: ensure tuning.lua is parsed (even without analyzer engine)."""

    tuning = getattr(engine, "tuning", None) if engine is not None else None
    if tuning is not None:
        return tuning

    try:
        from core.analyzer import TuningResolver  # type: ignore
        content = ""
        if engine is not None:
            content = engine.read_file("scripts/tuning.lua") or engine.read_file("tuning.lua") or ""
        if (not content) and store_meta:
            hint = str(store_meta.get("scripts_zip") or "").strip()
            if hint:
                try:
                    import zipfile
                    with zipfile.ZipFile(hint, "r") as z:
                        content = z.read("scripts/tuning.lua").decode("utf-8", errors="replace")
                except Exception:
                    content = ""
        if not content:
            return None
        tuning = TuningResolver(content)
        if engine is not None:
            try:
                engine.tuning = tuning
            except Exception:
                pass
        return tuning
    except Exception:
        return None


def _enrich_cooking_recipe(raw: Dict[str, Any], *, name: Optional[str] = None, tuning: Any = None) -> Dict[str, Any]:
    """Return a safe copy of cooking recipe dict with optional tuning traces.

    Adds:
      - name (if missing)
      - _tuning: { field -> tuning.trace_expr(raw_string) } for any string that contains "TUNING"
    """
    out: Dict[str, Any] = dict(raw or {})
    if name and not out.get("name"):
        out["name"] = name

    if tuning is None:
        return out

    traces: Dict[str, Any] = {}
    for k, v in list(out.items()):
        if isinstance(v, str) and ("TUNING" in v):
            try:
                tr = tuning.trace_expr(v)
                traces[str(k)] = tr
                # If resolvable, inline final value so UI can show both value + expr.
                if isinstance(tr.get("value"), (int, float)):
                    out[k] = tr.get("value")
            except Exception:
                traces[str(k)] = {"expr": v, "value": None, "expr_resolved": v, "refs": {}}

    if traces:
        out["_tuning"] = traces
    return out



class PlanRequest(BaseModel):
    inventory: Dict[str, float] = Field(default_factory=dict)
    builder_tag: Optional[str] = None
    strict: bool = False
    limit: int = 200


class MissingRequest(BaseModel):
    name: str
    inventory: Dict[str, float] = Field(default_factory=dict)


class CookingFindRequest(BaseModel):
    inventory: Dict[str, float] = Field(default_factory=dict)
    limit: int = 200


class CookingSimulateRequest(BaseModel):
    slots: Dict[str, float] = Field(default_factory=dict)
    return_top: int = 25


class CookingExploreRequest(BaseModel):
    slots: Dict[str, float] = Field(default_factory=dict)
    available: List[str] = Field(default_factory=list)
    limit: int = 200


@router.get("/meta")
def meta(request: Request, store: CatalogStore = Depends(get_store)):
    m = store.meta()
    m.update({"schema_version": store.schema_version()})

    # icon config (public)
    svc = getattr(request.app.state, "icon_service", None)
    if svc is not None:
        try:
            m.update({"icon": svc.cfg.to_public_dict()})
        except Exception:
            pass


    # runtime analyzer availability (optional)
    eng = _get_engine(request)
    m.update({"analyzer_enabled": bool(eng)})
    if eng is not None:
        try:
            m.update(
                {
                    "engine_mode": str(getattr(eng, "mode", "") or ""),
                    "scripts_file_count": len(getattr(eng, "file_list", []) or []),
                }
            )
        except Exception:
            pass

    # tuning traces for UI (optional; requires scripts mounted)
    tuning = _ensure_tuning(eng, store.meta())
    if tuning is not None:
        try:
            m.update({"tuning_enabled": True, "tuning_count": len(getattr(tuning, "raw_map", {}) or {})})
        except Exception:
            m.update({"tuning_enabled": True})
    else:
        m.update({"tuning_enabled": False})

    # tuning trace index (optional; built offline)
    tstore = _get_tuning_trace_store(request)
    if tstore is not None:
        try:
            m.update({"tuning_trace_enabled": True, "tuning_trace_count": tstore.count()})
        except Exception:
            m.update({"tuning_trace_enabled": True})
    else:
        m.update({"tuning_trace_enabled": False})

    # i18n (optional)
    iindex = _get_i18n_index_store(request)
    if iindex is not None:
        try:
            m.update({"i18n": iindex.public_meta()})
        except Exception:
            pass
    else:
        isvc = getattr(request.app.state, "i18n_service", None)
        if isvc is not None:
            try:
                scripts_zip_hint = str((m or {}).get("scripts_zip") or "").strip() or None
                m.update({"i18n": isvc.public_meta(engine=eng, scripts_zip_hint=scripts_zip_hint)})
            except Exception:
                pass

    etag = f'W/"meta-{int(store.mtime())}"'
    headers = _cache_headers(request, max_age=60, etag=etag)
    return _json(m, headers=headers)


@router.get("/tuning/trace")
def tuning_trace(
    request: Request,
    key: Optional[str] = None,
    prefix: Optional[str] = None,
    limit: int = Query(2000, ge=1, le=10000),
):
    """Return tuning trace entries by key or prefix (from tuning trace index)."""
    store = _get_tuning_trace_store(request)
    if store is None:
        return {"enabled": False, "trace": None, "traces": {}, "count": 0}

    if key:
        trace = store.get(str(key))
        return {"enabled": True, "key": str(key), "trace": trace}

    pref = str(prefix or "").strip()
    traces = store.get_prefix(pref, limit=int(limit))
    return {"enabled": True, "prefix": pref, "traces": traces, "count": len(traces)}


@router.get("/assets")
def assets(request: Request, store: CatalogStore = Depends(get_store)):
    mp = store.assets(include_icon_only=True)

    svc = getattr(request.app.state, "icon_service", None)
    icon_cfg = None
    if svc is not None:
        try:
            icon_cfg = svc.cfg.to_public_dict()
        except Exception:
            icon_cfg = None

    etag = f'W/"assets-{int(store.mtime())}-{len(mp)}"'
    headers = _cache_headers(request, max_age=300, etag=etag)
    return _json(
        {"assets": mp, "count": len(mp), "icon": icon_cfg or {"mode": "off", "static_base": "/static/data/icons", "api_base": "/api/v1/icon"}},
        headers=headers,
    )


@router.get("/catalog/index")
def catalog_index(
    request: Request,
    store: CatalogStore = Depends(get_store),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
):
    items, total = store.catalog_index_page(offset=int(offset), limit=int(limit))

    svc = getattr(request.app.state, "icon_service", None)
    icon_cfg = None
    if svc is not None:
        try:
            icon_cfg = svc.cfg.to_public_dict()
        except Exception:
            icon_cfg = None

    etag = f'W/"catalog-{int(store.mtime())}-{total}"'
    headers = _cache_headers(request, max_age=300, etag=etag)
    return _json(
        {
            "items": items,
            "count": len(items),
            "total": total,
            "offset": int(offset),
            "limit": int(limit),
            "icon": icon_cfg or {"mode": "off", "static_base": "/static/data/icons", "api_base": "/api/v1/icon"},
        },
        headers=headers,
    )


@router.get("/catalog/search")
def catalog_search(
    request: Request,
    q: str = Query(..., min_length=1),
    store: CatalogStore = Depends(get_store),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
):
    name_lookup: Optional[Dict[str, str]] = None
    iindex = _get_i18n_index_store(request)
    i18n_stamp = ""
    if iindex is not None and _has_cjk(q):
        try:
            name_lookup = iindex.names("zh")
            i18n_stamp = f"-i18n{int(getattr(iindex, 'mtime', lambda: 0)())}"
        except Exception:
            name_lookup = None
    items, total = store.catalog_search(q, offset=int(offset), limit=int(limit), name_lookup=name_lookup)
    q_sig = hashlib.sha1(str(q).encode("utf-8")).hexdigest()[:8]
    etag = f'W/"catalog-search-{int(store.mtime())}-{q_sig}-{total}{i18n_stamp}"'
    headers = _cache_headers(request, max_age=60, etag=etag)
    return _json({"q": q, "items": items, "count": len(items), "total": total, "offset": int(offset), "limit": int(limit)}, headers=headers)

@router.get("/i18n")
def i18n_meta(request: Request, store: CatalogStore = Depends(get_store)):
    """Return i18n capability + available languages."""
    iindex = _get_i18n_index_store(request)
    if iindex is not None:
        try:
            meta = iindex.public_meta()
            etag = f'W/"i18n-meta-{int(getattr(iindex, "mtime", lambda: 0)())}-{meta.get("langs")}"'
            headers = _cache_headers(request, max_age=300, etag=etag)
            return _json(meta, headers=headers)
        except Exception:
            return _json({"enabled": False, "langs": [], "ui_langs": [], "modes": ["en", "zh", "id"], "default_mode": "en"})
    return _json({"enabled": False, "langs": [], "ui_langs": [], "modes": ["en", "zh", "id"], "default_mode": "en"})


@router.get("/i18n/ui/{lang}")
def i18n_ui(lang: str, request: Request):
    """Return UI strings for the given language."""
    store = _get_i18n_index_store(request)
    if store is None:
        return _json({"lang": str(lang), "strings": {}, "count": 0, "enabled": False})
    try:
        mp = store.ui_strings(str(lang))
    except Exception:
        mp = {}
    etag = f'W/"i18n-ui-{int(getattr(store, "mtime", lambda: 0)())}-{lang}-{len(mp)}"'
    headers = _cache_headers(request, max_age=600, etag=etag)
    return _json({"lang": str(lang), "strings": mp, "count": len(mp or {}), "enabled": bool(mp)}, headers=headers)


@router.get("/i18n/names/{lang}")
def i18n_names(lang: str, request: Request, store: CatalogStore = Depends(get_store)):
    """Return id->localized name mapping for items in the current catalog."""
    iindex = _get_i18n_index_store(request)
    if iindex is not None:
        try:
            mp = iindex.names(str(lang))
        except Exception:
            mp = {}
        if mp:
            etag = f'W/"i18n-names-{int(getattr(iindex, "mtime", lambda: 0)())}-{lang}-{len(mp)}"'
            headers = _cache_headers(request, max_age=600, etag=etag)
            return _json({"lang": str(lang), "names": mp, "count": len(mp or {})}, headers=headers)
    return _json({"lang": str(lang), "names": {}, "count": 0})


@router.get("/i18n/tags/{lang}")
def i18n_tags(lang: str, request: Request):
    """Return tag->localized label mapping (with optional source meta)."""
    store = _get_i18n_index_store(request)
    if store is None:
        return _json({"lang": str(lang), "tags": {}, "meta": {}, "count": 0})
    try:
        mp = store.tags(str(lang))
        meta = store.tags_meta(str(lang))
    except Exception:
        mp, meta = {}, {}
    etag = f'W/"i18n-tags-{int(getattr(store, "mtime", lambda: 0)())}-{lang}-{len(mp)}"'
    headers = _cache_headers(request, max_age=600, etag=etag)
    return _json({"lang": str(lang), "tags": mp, "meta": meta, "count": len(mp or {})}, headers=headers)


@router.get("/items/{item_id}")
def item_detail(item_id: str, request: Request, store: CatalogStore = Depends(get_store)):
    """Return best-effort item-centric view.

    This endpoint is used by the /catalog UI.
    """
    q = (item_id or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="empty item_id")

    # presentation asset + item metadata (if any)
    asset = store.get_asset(q) or store.get_asset(q.lower())
    item = store.get_item(q) or store.get_item(q.lower())

    # craft references
    craft_used_in = store.list_by_ingredient(q) or store.list_by_ingredient(q.lower())
    craft_produced_by = store.list_by_product(q) or store.list_by_product(q.lower())

    # cooking references
    cook_used_in = store.list_cooking_by_ingredient(q) or store.list_cooking_by_ingredient(q.lower())
    cook_rec = store.get_cooking_recipe(q) or store.get_cooking_recipe(q.lower())

    return {
        "item_id": q,
        "item": item,
        "asset": asset,
        "craft": {"used_in": craft_used_in, "produced_by": craft_produced_by},
        "cooking": {
            "as_recipe": (
                _enrich_cooking_recipe(
                    cook_rec.raw,
                    name=cook_rec.name,
                    tuning=_ensure_tuning(_get_engine(request), store.meta()),
                )
                if cook_rec else None
            ),
            "used_in": cook_used_in,
        },
    }



@router.get("/icon/{item_id}.png")
def icon_png(item_id: str, request: Request, store: CatalogStore = Depends(get_store)):
    """Return an item icon as PNG.

    This endpoint supports dynamic generation (atlas+xml + tex) when enabled.
    In all modes, it caches to the static icons directory as <id>.png.
    """

    svc = getattr(request.app.state, "icon_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Icon service not configured")

    asset = store.get_asset(item_id)
    p = svc.ensure_icon(item_id, asset)
    if not p:
        raise HTTPException(status_code=404, detail=f"Icon not found: {item_id}")

    return FileResponse(path=str(p), media_type="image/png")


# ----------------- craft browse -----------------


@router.get("/craft/filters")
def craft_filters(store: CatalogStore = Depends(get_store)):
    order, defs = store.list_filters()
    return {"order": order, "defs": defs}


@router.get("/craft/tabs")
def craft_tabs(store: CatalogStore = Depends(get_store)):
    return {"tabs": store.list_tabs()}


@router.get("/craft/tags")
def craft_tags(store: CatalogStore = Depends(get_store)):
    return {"tags": store.list_tags()}


@router.get("/craft/filters/{filter_name}/recipes")
def craft_filter_recipes(filter_name: str, store: CatalogStore = Depends(get_store)):
    names = store.list_by_filter(filter_name)
    return {"filter": filter_name, "recipes": names}


@router.get("/craft/tabs/{tab}/recipes")
def craft_tab_recipes(tab: str, store: CatalogStore = Depends(get_store)):
    names = store.list_by_tab(tab)
    return {"tab": tab, "recipes": names}


@router.get("/craft/tags/{tag}/recipes")
def craft_tag_recipes(tag: str, store: CatalogStore = Depends(get_store)):
    names = store.list_by_tag(tag)
    return {"tag": tag, "recipes": names}


@router.get("/craft/ingredients/{item}/recipes")
def craft_ingredient_recipes(item: str, store: CatalogStore = Depends(get_store)):
    names = store.list_by_ingredient(item)
    return {"ingredient": item, "recipes": names}


# ----------------- craft recipe -----------------

@router.get("/craft/products/{item}/recipes")
def craft_product_recipes(item: str, store: CatalogStore = Depends(get_store)):
    names = store.list_by_product(item)
    return {"product": item, "recipes": names}



@router.get("/craft/recipes/search")
def craft_search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
    store: CatalogStore = Depends(get_store),
):
    name_lookup: Optional[Dict[str, str]] = None
    iindex = _get_i18n_index_store(request)
    if iindex is not None and _has_cjk(q):
        try:
            name_lookup = iindex.names("zh")
        except Exception:
            name_lookup = None
    return {"q": q, "results": store.search(q, limit=limit, name_lookup=name_lookup)}


@router.get("/craft/recipes/{name}")
def craft_recipe(name: str, store: CatalogStore = Depends(get_store)):
    rec = store.get_recipe(name)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recipe not found: {name}")
    return {"recipe": rec.raw}


# ----------------- craft planning -----------------


@router.post("/craft/plan")
def craft_plan(req: PlanRequest, store: CatalogStore = Depends(get_store)):
    inv = normalize_inventory(req.inventory)
    limit = int(req.limit or 200)
    limit = max(1, min(limit, 2000))

    recipes: List[CraftRecipe] = store.iter_recipes()
    recipes.sort(key=lambda x: x.name)

    ok, blocked = craftable_recipes(recipes, inv, builder_tag=req.builder_tag, strict=bool(req.strict))
    ok_names = [r.name for r in ok[:limit]]
    return {"craftable": ok_names, "blocked": blocked[:limit], "count": len(ok_names)}


@router.post("/craft/missing")
def craft_missing(req: MissingRequest, store: CatalogStore = Depends(get_store)):
    rec = store.get_recipe(req.name)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recipe not found: {req.name}")
    inv = normalize_inventory(req.inventory)
    miss = missing_for(rec, inv)
    return {"name": rec.name, "missing": [m.__dict__ for m in miss]}


# ----------------- cooking browse -----------------


@router.get("/cooking/recipes")
def cooking_all(store: CatalogStore = Depends(get_store)):
    recipes: List[CookingRecipe] = store.iter_cooking_recipes()
    names = sorted([r.name for r in recipes])
    return {"recipes": names, "count": len(names)}


@router.get("/cooking/foodtypes")
def cooking_foodtypes(store: CatalogStore = Depends(get_store)):
    return {"foodtypes": store.list_cooking_foodtypes()}


@router.get("/cooking/tags")
def cooking_tags(store: CatalogStore = Depends(get_store)):
    return {"tags": store.list_cooking_tags()}


@router.get("/cooking/ingredients")
def cooking_ingredients(store: CatalogStore = Depends(get_store)):
    raw, source = store.cooking_ingredients_with_fallback()
    items: List[Dict[str, Any]] = []
    if raw:
        for iid, data in raw.items():
            tags = data.get("tags")
            if not isinstance(tags, (dict, list)):
                tags = {}
            items.append(
                {
                    "id": iid,
                    "tags": tags,
                    "foodtype": data.get("foodtype"),
                    "uses": len(store.list_cooking_by_ingredient(iid)),
                }
            )
    elif source == "card_ingredients":
        for iid in store.list_cooking_ingredients():
            items.append(
                {
                    "id": iid,
                    "tags": {},
                    "foodtype": None,
                    "uses": len(store.list_cooking_by_ingredient(iid)),
                }
            )

    items.sort(key=lambda x: (-int(x.get("uses") or 0), str(x.get("id") or "")))
    return {"ingredients": items, "count": len(items), "source": source}


@router.get("/cooking/foodtypes/{foodtype}/recipes")
def cooking_foodtype_recipes(foodtype: str, store: CatalogStore = Depends(get_store)):
    return {"foodtype": foodtype, "recipes": store.list_cooking_by_foodtype(foodtype)}


@router.get("/cooking/tags/{tag}/recipes")
def cooking_tag_recipes(tag: str, store: CatalogStore = Depends(get_store)):
    return {"tag": tag, "recipes": store.list_cooking_by_tag(tag)}


@router.get("/cooking/ingredients/{item}/recipes")
def cooking_ingredient_recipes(item: str, store: CatalogStore = Depends(get_store)):
    return {"ingredient": item, "recipes": store.list_cooking_by_ingredient(item)}


# ----------------- cooking recipe -----------------


@router.get("/cooking/recipes/search")
def cooking_search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
    store: CatalogStore = Depends(get_store),
):
    name_lookup: Optional[Dict[str, str]] = None
    iindex = _get_i18n_index_store(request)
    if iindex is not None and _has_cjk(q):
        try:
            name_lookup = iindex.names("zh")
        except Exception:
            name_lookup = None
    return {"q": q, "results": store.search_cooking(q, limit=limit, name_lookup=name_lookup)}


@router.get("/cooking/recipes/{name}")
def cooking_recipe(name: str, request: Request, store: CatalogStore = Depends(get_store)):
    rec = store.get_cooking_recipe(name)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Cooking recipe not found: {name}")
    eng = _get_engine(request)
    tuning = _ensure_tuning(eng, store.meta())
    return {"recipe": _enrich_cooking_recipe(rec.raw, name=rec.name, tuning=tuning)}


# ----------------- cooking helpers -----------------


@router.post("/cooking/find")
def cooking_find(req: CookingFindRequest, store: CatalogStore = Depends(get_store)):
    inv = normalize_counts(req.inventory)
    limit = max(1, min(int(req.limit or 200), 2000))

    recipes = store.iter_cooking_recipes()
    cookable = find_cookable(recipes, inv, limit=limit)
    names = [r.name for r in cookable]

    return {
        "cookable": names,
        "count": len(names),
        "note": "only recipes with card_ingredients are searchable/simulatable",
    }


@router.post("/cooking/explore")
def cooking_explore(req: CookingExploreRequest, store: CatalogStore = Depends(get_store)):
    recipes = store.iter_cooking_recipes()
    ingredients, _ = store.cooking_ingredients_with_fallback()
    return explore_cookpot(
        recipes,
        req.slots,
        ingredients=ingredients,
        available=req.available,
        limit=int(req.limit or 200),
    )


@router.post("/cooking/simulate")
def cooking_simulate(req: CookingSimulateRequest, request: Request, store: CatalogStore = Depends(get_store)):
    recipes = store.iter_cooking_recipes()
    ingredients, _ = store.cooking_ingredients_with_fallback()
    out = simulate_cookpot(recipes, req.slots, return_top=int(req.return_top or 25), ingredients=ingredients)

    # Attach result recipe details if available.
    if out.get("ok") and out.get("result"):
        rec = store.get_cooking_recipe(str(out.get("result")))
        if rec:
            eng = _get_engine(request)
            tuning = _ensure_tuning(eng, store.meta())
            out["recipe"] = _enrich_cooking_recipe(rec.raw, name=rec.name, tuning=tuning)

    return out


@router.get("/analyze/prefab/{name}")
def analyze_prefab(name: str, request: Request):
    """Parse a prefab lua file and return a structured report.

    Requires the server to be started with analyzer enabled (scripts mounted).
    """
    eng = getattr(request.app.state, "engine", None)
    if eng is None:
        raise HTTPException(status_code=400, detail="analyzer disabled (no scripts source mounted)")

    q = (name or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="empty name")

    try:
        path = eng.find_file(q, fuzzy=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not path:
        raise HTTPException(status_code=404, detail=f"file not found for: {q}")

    content = eng.read_file(path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"cannot read: {path}")

    from core.analyzer import LuaAnalyzer
    rep = LuaAnalyzer(content, path=path).get_report()
    return {"query": q, "path": path, "report": rep}
