# Wagstaff CLI Role Plan (v4.0.0-dev)

Goal: make the CLI an engineering console with clear roles and low cognitive load.

Install entrypoint (once per env): `python -m pip install -e ".[cli]"`.

## 1. Role Layers

- **Dash (entry)**
  - Purpose: project overview and runtime snapshot (objective, tasks, artifacts, freshness, quality).
  - Command: `wagstaff dash`

- **Health (env/artifact checks)**
  - Purpose: verify config and key artifacts (info-only, no blocking).
  - Command: `wagstaff doctor`

- **Query (knowledge lookup)**
  - Purpose: query recipes/cooking/prefab analysis for day-to-day lookup.
  - Command: `wagstaff wiki`

- **Explore (source analysis)**
  - Purpose: inspect source structure and Lua parsing for parser development.
  - Command: `wagstaff exp`

- **Mgmt (project management)**
  - Purpose: show/sync milestones and active tasks.
  - Command: `wagstaff mgmt`
  - Tip: `wagstaff mgmt check` for DEV_GUIDE emphasis
  - i18n: `--lang` or `WAGSTAFF_LANG=zh|en`


- **Build (index outputs)**
  - Purpose: generate data/index + data/reports artifacts.
  - Commands:
    - `wagstaff resindex` resource index
    - `wagstaff catalog2` catalog v2
    - `wagstaff catalog-sqlite` catalog sqlite v4
    - `wagstaff catindex` compact catalog index
    - `wagstaff i18n` i18n index
    - `wagstaff icons` icons + icon index
    - `wagstaff farming-defs` farming defs
    - `wagstaff mechanism-index build` mechanism index
    - `wagstaff behavior-graph` behavior graph index
    - `wagstaff worldgen build` worldgen 结构索引
    - `wagstaff worldgen topo` worldgen S3 拓扑骨架
    - Tip: `wagstaff mechanism-index validate` / `wagstaff mechanism-index diff`
    - `wagstaff index-manifest` index manifest

- **Quality (coverage checks)**
  - Purpose: quality gate (default info-only); reports generated via report hub.
  - Command:
    - `wagstaff quality` (includes sqlite + mechanism checks)
  - Report refresh: `wagstaff report build --quality`

- **Ops (service)**
  - Purpose: run WebCraft for UI validation.
  - Command: `wagstaff web`

- **Server (DST ops)**
  - Purpose: start/stop/update/backup/restore DST servers via screen.
  - Command: `wagstaff server` (interactive: `wagstaff server ui`)

- **Utility (support)**
  - Purpose: snapshots, reports, macro scans.
  - Commands: `wagstaff snap` / `wagstaff report` / `wagstaff samples` / `wagstaff farming-sim`
  - Report hub: `wagstaff report build --all` / `wagstaff report build --stats-gap` / `wagstaff report list` / `wagstaff report open`
  - Static coverage: `wagstaff report build --quality` includes static mechanics baseline
  - Portal: `wagstaff portal build` / `wagstaff portal list` / `wagstaff portal open`

## 2. Command Overview

- Entry
  - `wagstaff` / `wagstaff dash`
- Build
  - `wagstaff resindex` / `wagstaff catalog2` / `wagstaff catalog-sqlite` / `wagstaff catindex`
  - `wagstaff i18n` / `wagstaff icons` / `wagstaff farming-defs` / `wagstaff mechanism-index build` / `wagstaff behavior-graph`
  - `wagstaff worldgen build` / `wagstaff worldgen topo`
  - `wagstaff index-manifest`
- Quality
  - `wagstaff quality`
- Service
  - `wagstaff web`
- Server
  - `wagstaff server` / `wagstaff server ui`
- Query + Analysis
  - `wagstaff wiki` / `wagstaff exp`
- Management
  - `wagstaff mgmt`
- Utilities
  - `wagstaff snap` / `wagstaff report` / `wagstaff portal` / `wagstaff samples` / `wagstaff farming-sim`

## 3. Operating Principles

- CLI is for input/output orchestration; core parsing belongs in `core/`.
- Build artifacts always land in `data/`; CLI consumes `data/index` + `data/reports`.
- `wagstaff dash` is the default entry point (high density, non-blocking).
