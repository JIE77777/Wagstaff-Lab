# Wagstaff-Lab 开发规范 (v3.2)

本指南用于约束核心架构边界与开发协作方式，确保可维护与可扩展。

## 0. 快速必读（人/LLM）

- **本文件是强制入口**：任何架构/入口/产物变更都必须先对照并更新本文件。
- **执行顺序建议**：`README.md` → `DEV_GUIDE.md` → `PROJECT_MANAGEMENT.md` → `CATALOG_V2_SPEC.md`。
- **规范优先级**：若文档冲突，以 `DEV_GUIDE.md` 为准。

### DEV_GUIDE_META

```yaml
dev_guide:
  version: v3.2
  must_update_on:
    - 架构/目录调整
    - CLI/Web/Server 入口变更
    - 索引/产物结构变更
    - 依赖/构建流程变更
  entrypoints:
    - wagstaff
    - make
  management:
    - docs/management/PROJECT_MANAGEMENT.md
    - PROJECT_STATUS.json
```

## 1. 分层职责

- `core/`：解析、索引、算法与数据模型。不得依赖 `apps/` 或 `devtools/`。
- `core/schemas/`：核心数据结构与元信息规范（仅类型/结构，不含流程）。
- `core/indexers/`：索引构建逻辑（依赖 `core/` 但不触碰上层）。
- `apps/cli/`：CLI 交互层。调用 `core/`，仅做输入/输出组织。
- `apps/cli/commands/`：CLI 子命令实现（dashboard/doctor/wiki/explorer 等）。
- `apps/server/`：服务器运维（DST 运行/备份/恢复），与数据分析解耦。
- `apps/webcraft/`：WebCraft 服务层（API + UI）。只通过索引产物与 `core/` 暴露的能力。
- `devtools/`：构建、报表、快照等流程工具。
- `data/`：所有产物、报告、索引、静态资源的统一落盘目录。
- CLI 角色与职责见 `docs/guides/CLI_GUIDE.md`。

## 2. 依赖与导入约定

- 依赖方向：`apps/`、`devtools/` -> `core/`。
- 入口脚本只挂载项目根目录到 `sys.path`，通过 `core.*` / `apps.*` / `devtools.*` 进行导入。
- `core/` 不得自行修改 `sys.path`。
- 任何跨层访问，优先通过 `core` 的稳定 API，而非直接读文件或 copy 逻辑。

## 3. 包管理 (pyproject.toml)

- 依赖统一由 `pyproject.toml` 管理，禁止散落在脚本内。
- 采用可选依赖分组：`cli` / `web` / `icons` / `quality` / `all`。
- 入口注册统一通过：`python -m pip install -e ".[cli]"`（需要完整能力时用 `.[all]`）。

## 4. 数据产物与命名

- 统一落盘到 `data/`，并带版本号后缀，例如：
  - `data/index/wagstaff_catalog_v2.json`
  - `data/index/wagstaff_catalog_v2.sqlite`
  - `data/index/wagstaff_icon_index_v1.json`
- 产物默认不入库：`data/index/` 与 `data/static/icons/` 由工具生成，需要时用 `make catalog` / `make icons` 重建。
- 产物需携带统一元信息（schema / generated / tool / sources / scripts hash）。
- WebCraft UI 不应直接读取原始脚本或 datastream，仅消费 `data/index` 等稳定产物。
- Catalog v2 产物新增 `cooking_ingredients` 字段用于料理食材 tags 索引。

## 5. WebCraft 约定

- API 统一在 `/api/v1` 下，UI 与 API 使用同一 `root_path`。
- UI 仅通过 API 访问数据；静态资源来自 `data/static/`。
- 新增字段须保证向后兼容或同步更新 `schema_version`。
- WebCraft 运行时优先使用 `data/index/wagstaff_catalog_v2.sqlite`，缺失时回退 JSON。
- i18n 仅使用 `data/index/wagstaff_i18n_v1.json`（运行时不解析 PO）。
- WebCraft 应用静态资源（CSS/字体等）放在 `apps/webcraft/static/`，对外挂载为 `/static/app`；数据产物静态资源（如图标）继续落盘 `data/static/` 并对外挂载 `/static/data`。

## 5.1 UI 设计规范

- 任何 UI 设计/重构任务默认使用 `frontend-design` skill 产出方案与代码。

## 6. 变更与文档

- 重要重构必须同步更新：
  - `README.md`
  - `docs/guides/DEV_GUIDE.md`
  - `PROJECT_STATUS.json`
  - `docs/management/PROJECT_MANAGEMENT.md`
  - `docs/` 相关文档
- 所有结构调整需记录到 `RECENT_LOGS`。

## 6.1 变更检查清单（强制）

- [ ] DEV_GUIDE 是否需要更新（架构/入口/产物/依赖）
- [ ] PROJECT_MANAGEMENT 是否需要更新（里程碑/任务）
- [ ] PROJECT_STATUS 是否同步（RECENT_LOGS/任务）
- [ ] 文档入口是否一致（README / SPEC / ROADMAP）

## 6.2 Git 流程（强制）

- 分支命名：`feat/` `fix/` `refactor/` `docs/` `chore/` `ui/`
- 提交信息：`type(scope): summary`（示例：`feat(cooking): add explore scoring`）
- 任何 `push`（含本地）必须满足：
  - `git status` 为 clean
  - `git pull --rebase` 同步最新
  - 完成与改动相关的自检（参考 6.1 检查清单）
- 禁止对共享分支强推（`--force`/`--force-with-lease`）
- 收尾（强制）：
  - `git diff --stat` 自检改动范围，确认未误入 `data/index`/`data/static/icons`
  - `PROJECT_STATUS.json` 追加 `RECENT_LOGS`（必要时同步 README/管理文档）
  - `git add -A` → `git commit -m "type(scope): summary"` → `git status` clean

## 7. Snapshot 友好开发规范 (面向后续开发)

- 公开接口集中在少数入口文件（例如 `core/engine.py`、`apps/*/app.py`），避免散落式 API。
- 模块顶部写清楚职责与输入/输出约束，复杂模块必须有模块级 docstring。
- 对外数据结构必须有字段说明（注释或类型定义），避免“隐式字段”。
- 重要函数保持稳定签名，新增参数必须给默认值并写清变更意图。
- 新增索引/产物必须落盘 `data/` 并记录 schema_version 与生成来源。
- 关键流程写最小示例（1-3 行 usage），便于快照直接引用。

## 8. LLM 快照与文档导出 (snapshot.py)

- `devtools/snapshot.py` 是统一的 LLM 友好导出工具；`wagstaff snap` 默认使用 llm 模板输出 `project_context.txt`。
- 模板集中在 `conf/snapshot_templates.json`，通过 `sections` 控制 env/tree/inventory/contents/stats 等模块输出。
- 聚焦导出使用 `--focus path|glob`（可多次传入），默认仍保留 `README.md`/`PROJECT_STATUS.json` 作为上下文。
- 若需更清爽输出，可用 `--no-tree`/`--no-inventory`/`--no-contents` 等开关精简。
- 重要重构必须同步更新 `PROJECT_STATUS.json`/`README.md`，确保快照上下文准确。

## 9. 任务入口 (Makefile)

- `make resindex` / `make catalog` / `make catalog-index`
- `make catalog-sqlite`
- `make i18n` / `make icons`
- `make quality` / `make gate`
- `make webcraft` / `make snap`

## 10. 最低自检清单

- `wagstaff dash` (主界面可运行)
- `python devtools/build_catalog_v2.py --silent`
- `python devtools/quality_gate.py` (信息提示，CI 可加 --enforce/--strict)
- `python devtools/snapshot.py --mode llm --plan` (快照计划可生成)
- `python devtools/serve_webcraft.py --help` (需要 uvicorn)
