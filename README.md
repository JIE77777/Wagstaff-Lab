# Wagstaff-Lab (v4.0.0-dev)

Wagstaff-Lab 是 DST（Don't Starve Together）数据实验室：负责索引、分析与 WebCraft UI，所有上层展示都基于稳定的索引产物。当前架构为 `core/` 解析与索引、`apps/` 应用层、`devtools/` 构建与报告工具。

## 必读

- `docs/guides/DEV_GUIDE.md`：开发规范与强制约束
- `docs/management/PROJECT_MANAGEMENT.md`：管理与进度执行入口

## 当前能力

- **Catalog v2**：以物品为中心的可标签化目录，含 stats 与 assets
- **Tuning trace**：可选输出 TUNING 解析链路
- **i18n index**：名称 + 描述/台词 + UI 词条（数据层与语言解耦）
- **Icon pipeline**：静态图标 + 动态回退
- **Mechanism index**：组件解析 + prefab 链路 + SQLite 输出
- **Behavior graph (MVP)**：stategraph/brain 结构化索引
- **Farming simulation (lightweight)**：基于 farming defs 的轻量模拟 CLI
- **Quality gate + Report hub**：质量门禁 + 报告汇总入口
- **Index manifest**：索引清单与版本汇总
- **WebCraft**：FastAPI UI，严格使用索引产物

## 安装（pyproject 入口）

建议在 `dst_lab` 环境中执行：

```bash
python -m pip install -e ".[cli]"
```

全量依赖（web + icons + quality）：

```bash
python -m pip install -e ".[all]"
```

CLI 入口为 `wagstaff`。

## 配置 DST 路径

在 `conf/settings.ini` 中配置 `DST_ROOT`，或通过命令参数 `--dst-root` 覆盖。

示例：
```
[PATHS]
DST_ROOT=/path/to/dontstarvetogether_dedicated_server
```

## 构建流程

所有产物落盘在 `data/`，并带版本后缀。

一键构建：
```bash
make all
```
包含 farming-defs/farming-fixed（耕种机制索引与固定解索引）与质量门禁。

报告构建：
```bash
wagstaff report build --all
```

更多构建子命令见 `docs/guides/CLI_GUIDE.md`。

## 启动 WebCraft

```bash
wagstaff web --host 0.0.0.0 --port 20000 --reload-catalog
```

WebCraft 优先读取 `data/index/wagstaff_catalog_v2.sqlite`（缺失时回退 JSON）。
i18n 仅使用 `data/index/wagstaff_i18n_v1.json`（运行时不解析 PO，包含 names/desc/quotes/ui/tags）。

默认本地启动：
```bash
wagstaff web
```

## CLI 核心命令

- `wagstaff` / `wagstaff dash`：项目概览面板
- `wagstaff doctor`：环境与产物检查（信息提示）
- `wagstaff resindex`：资源索引构建
- `wagstaff catalog2`：Catalog v2 构建
- `wagstaff catalog-sqlite`：Catalog SQLite v4 构建
- `wagstaff catindex`：Catalog 紧凑索引构建
- `wagstaff mechanism-index`：机制索引（build/validate/diff）
- `wagstaff behavior-graph`：行为图谱索引
- `wagstaff farming-sim`：耕种轻量模拟（基于 farming defs）
- `wagstaff quality`：质量/校验总入口
- `wagstaff report`：报告中心（build/list/open）
- `wagstaff portal`：管理+报告+质量聚合视图
- `wagstaff web`：启动 WebCraft
- `wagstaff server`：DST 服务器管理（screen 会话）

完整命令清单见 `docs/guides/CLI_GUIDE.md`。

## 服务器管理示例

```bash
wagstaff server status
wagstaff server ui
wagstaff server start
wagstaff server stop --timeout 40 --force
wagstaff server backup
wagstaff server restore --latest --yes --start
wagstaff server logs --shard master --follow
wagstaff server cmd "c_announce(\"hello\")"
```

## 关键产物

索引产物（data/index）：
```
data/index/wagstaff_resource_index_v1.json
data/index/wagstaff_catalog_v2.json
data/index/wagstaff_catalog_v2.sqlite
data/index/wagstaff_catalog_index_v1.json
data/index/wagstaff_farming_defs_v1.json
data/index/wagstaff_farming_fixed_v1.json
data/index/wagstaff_mechanism_index_v1.json
data/index/wagstaff_mechanism_index_v1.sqlite
data/index/wagstaff_behavior_graph_v1.json
data/index/wagstaff_i18n_v1.json
data/index/wagstaff_icon_index_v1.json
data/index/wagstaff_tuning_trace_v1.json
data/index/wagstaff_index_manifest.json
```

报告产物（data/reports，report hub 生成）：
```
data/reports/quality_gate_report.md
data/reports/mechanism_index_summary.md
data/reports/mechanism_crosscheck_report.md
data/reports/catalog_quality_report.md
data/reports/static_mechanics_coverage_report.md
data/reports/static_mechanics_coverage_report.json
data/reports/wagstaff_report_manifest.json
data/reports/index.html
data/reports/portal_index.html
```

## 项目结构

```
core/            解析 + 索引 + schemas
core/lua/        Lua 解析基元
core/parsers/    Prefab/Loot/Cooking 等解析器
core/indexers/   索引构建逻辑
core/schemas/    数据契约 + meta 辅助
apps/cli/        CLI dispatcher + commands
apps/server/     DST server ops (isolated from data analysis)
apps/webcraft/   WebCraft API + UI
devtools/        构建/报告/快照工具
conf/            配置与快照模板
data/            产物与报告
docs/            guides/ specs/ management/ architecture
```

WebCraft UI 模板与静态资源：
- `apps/webcraft/templates/`：HTML 模板
- `apps/webcraft/static/`：CSS/JS/字体（对外挂载 `/static/app`）

## 文档入口

- `docs/README.md`：文档索引
- `docs/guides/DEV_GUIDE.md`：开发规范
- `docs/guides/CLI_GUIDE.md`：CLI 角色与职责
- `docs/specs/CATALOG_V2_SPEC.md`：Catalog v2 规范
- `docs/management/ROADMAP.md`：项目路线图
- `docs/management/PROJECT_MANAGEMENT.md`：项目管理与进度
- `docs/management/VNEXT_REFACTOR_PLAN.md`：vNext 重构规划（破兼容版）
