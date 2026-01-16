# Wagstaff-Lab 开发规范 (v3.2)

本指南用于约束核心架构边界与开发协作方式，确保可维护与可扩展。

## 1. 分层职责

- `core/`：解析、索引、算法与数据模型。不得依赖 `apps/` 或 `devtools/`。
- `apps/cli/`：CLI 交互层。调用 `core/`，仅做输入/输出组织。
- `apps/webcraft/`：WebCraft 服务层（API + UI）。只通过索引产物与 `core/` 暴露的能力。
- `devtools/`：构建、报表、快照等流程工具。
- `data/`：所有产物、报告、索引、静态资源的统一落盘目录。

## 2. 依赖与导入约定

- 依赖方向：`apps/`、`devtools/` -> `core/`。
- 入口脚本负责挂载 `core/`（必要时 `apps/`）到 `sys.path`，`core/` 不得自行修改 `sys.path`。
- 任何跨层访问，优先通过 `core` 的稳定 API，而非直接读文件或 copy 逻辑。

## 3. 数据产物与命名

- 统一落盘到 `data/`，并带版本号后缀，例如：
  - `data/index/wagstaff_catalog_v2.json`
  - `data/index/wagstaff_icon_index_v1.json`
- 产物需携带元信息（scripts hash / schema_version / 构建时间）。
- WebCraft UI 不应直接读取原始脚本或 datastream，仅消费 `data/index` 等稳定产物。

## 4. WebCraft 约定

- API 统一在 `/api/v1` 下，UI 与 API 使用同一 `root_path`。
- UI 仅通过 API 访问数据；静态资源来自 `data/static/`。
- 新增字段须保证向后兼容或同步更新 `schema_version`。

## 5. 变更与文档

- 重要重构必须同步更新：
  - `README.md`
  - `PROJECT_STATUS.json`
  - `docs/` 相关文档
- 所有结构调整需记录到 `RECENT_LOGS`。

## 6. Snapshot 友好开发规范 (面向后续开发)

- 公开接口集中在少数入口文件（例如 `core/engine.py`、`apps/*/app.py`），避免散落式 API。
- 模块顶部写清楚职责与输入/输出约束，复杂模块必须有模块级 docstring。
- 对外数据结构必须有字段说明（注释或类型定义），避免“隐式字段”。
- 重要函数保持稳定签名，新增参数必须给默认值并写清变更意图。
- 新增索引/产物必须落盘 `data/` 并记录 schema_version 与生成来源。
- 关键流程写最小示例（1-3 行 usage），便于快照直接引用。

## 7. LLM 快照与文档导出 (snapshot.py)

- `devtools/snapshot.py` 是统一的 LLM 友好导出工具；`wagstaff snap` 默认使用 llm 模板输出 `project_context.txt`。
- 模板集中在 `conf/snapshot_templates.json`，通过 `sections` 控制 env/tree/inventory/contents/stats 等模块输出。
- 聚焦导出使用 `--focus path|glob`（可多次传入），默认仍保留 `README.md`/`PROJECT_STATUS.json` 作为上下文。
- 若需更清爽输出，可用 `--no-tree`/`--no-inventory`/`--no-contents` 等开关精简。
- 重要重构必须同步更新 `PROJECT_STATUS.json`/`README.md`，确保快照上下文准确。

## 8. 最低自检清单

- `python apps/cli/guide.py` (主界面可运行)
- `python devtools/build_catalog_v2.py --silent`
- `python devtools/snapshot.py --mode llm --plan` (快照计划可生成)
- `python devtools/serve_webcraft.py --help` (需要 uvicorn)
