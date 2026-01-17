# Wagstaff-Lab (v3)

Wagstaff-Lab 是 DST（Don't Starve Together）数据实验室：负责索引、分析与 WebCraft UI，所有上层展示都基于稳定的索引产物。当前架构为 `core/` 解析与索引、`apps/` 应用层、`devtools/` 构建与报告工具。

## 必读

- `docs/guides/DEV_GUIDE.md`：开发规范与强制约束
- `docs/management/PROJECT_MANAGEMENT.md`：管理与进度执行入口

## 当前能力

- **Catalog v2**：以物品为中心的可标签化目录，含 stats 与 assets
- **Tuning trace**：可选输出 TUNING 解析链路
- **i18n index**：名称 + UI 词条（数据层与语言解耦）
- **Icon pipeline**：静态图标 + 动态回退
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

或分步构建：
```bash
wagstaff resindex   # resource index
wagstaff catalog2   # catalog v2 (+ tuning trace)
wagstaff catindex   # compact catalog index
wagstaff i18n       # i18n index
wagstaff icons      # icon export + icon index
wagstaff catqa      # coverage/quality report
wagstaff quality    # info-only quality gate
```

可选：生成 SQLite 版本 catalog：
```bash
make catalog-sqlite
```

## 启动 WebCraft

```bash
wagstaff web --host 0.0.0.0 --port 20000 --reload-catalog
```

WebCraft 优先读取 `data/index/wagstaff_catalog_v2.sqlite`（缺失时回退 JSON）。
i18n 仅使用 `data/index/wagstaff_i18n_v1.json`（运行时不解析 PO）。

默认本地启动：
```bash
wagstaff web
```

## CLI 总览

- `wagstaff` / `wagstaff dash`：项目概览面板
- `wagstaff doctor`：环境与产物检查（信息提示）
- `wagstaff wiki`：配方/烹饪/Prefab 查询
- `wagstaff exp`：源码与 Lua 解析探索
- `wagstaff mgmt`：管理状态展示与同步
- `wagstaff server`：DST 服务器管理（screen 会话）
- `wagstaff snap`：LLM 快照导出

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

```
data/index/wagstaff_resource_index_v1.json
data/index/wagstaff_catalog_v2.json
data/index/wagstaff_catalog_v2.sqlite
data/index/wagstaff_catalog_index_v1.json
data/index/wagstaff_i18n_v1.json
data/index/wagstaff_icon_index_v1.json
data/index/wagstaff_tuning_trace_v1.json
data/reports/catalog_quality_report.md
```

## 项目结构

```
core/            解析 + 索引 + schemas
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

## 文档入口

- `docs/README.md`：文档索引
- `docs/guides/DEV_GUIDE.md`：开发规范
- `docs/guides/CLI_GUIDE.md`：CLI 角色与职责
- `docs/specs/CATALOG_V2_SPEC.md`：Catalog v2 规范
- `docs/management/ROADMAP.md`：项目路线图
- `docs/management/PROJECT_MANAGEMENT.md`：项目管理与进度
