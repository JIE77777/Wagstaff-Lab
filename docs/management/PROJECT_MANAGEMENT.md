# Wagstaff-Lab 项目管理总览 (v4.0.0-dev)

本文件是**执行层面的单一管理入口**。ROADMAP 仅保留长期方向，SPEC 仅描述数据/接口契约，PROJECT_STATUS 保持运行快照与近期记录。

## 0. 管理约定

- **战略方向**：`docs/management/ROADMAP.md`
- **vNext 重构规划**：`docs/management/VNEXT_REFACTOR_PLAN.md`
- **数据契约**：`docs/specs/CATALOG_V2_SPEC.md`
- **执行管理**：`docs/management/PROJECT_MANAGEMENT.md`（本文件）
- **运行快照**：`PROJECT_STATUS.json`

说明：不再使用 pm 工具，统一以文档与 JSON 状态文件管理进度。
工具化入口：`wagstaff mgmt status|sync|dump`。
建议：`wagstaff mgmt check` 作为变更前的必跑检查。

## 1. L0 目标（North Star）

对 DST 资源实现**可迁移、可检索、可解释**的全面理解与展示，产物可被 Web/CLI/后续数据库直接消费。

## 2. L1 里程碑（Milestones）

- **M3.0 架构拆分与入口统一**（完成）
  - core/apps 分层、CLI dispatcher、pyproject 入口、Makefile 任务体系
- **M3.1 Catalog v2 基线与 WebCraft 接入**（完成）
  - Catalog v2、icon index、tuning trace、WebCraft UI/接口对接
- **M3.2 质量与覆盖率提升**（进行中）
  - stats 解析覆盖、i18n 覆盖、质量报告持续迭代
- **M3.3 WebCraft 体验深化**（规划中）
  - 参考标杆：Food Guide（模拟/探索/统计）、DST Item List（双语+调试 ID）、Wiki Craft 表格化呈现
  - 三入口体验：Catalog/Craft/Cooking 结构一致，探索/模拟/百科模式清晰
  - 解释性输出：规则/条件/trace 可视化，配方链路与用途说明
  - catalog 分页/缓存与搜索改造（已落地）
  - Cooking 升级方案归档：`docs/archived/COOKING_UPGRADE.md`
- **M3.4 存储升级准备**（规划中）
  - SQLite/Parquet 迁移计划与 schema 对齐
  - SQLite catalog 派生产物与 WebCraft SQLite 优先加载（已落地）
- **M3.5 服务器运维集成**（完成）
  - wagstaff server 与独立运维模块

## 3. L2 需求分层（Pillars → Epics）

### 数据基础
- **E1 资源索引**：scripts + data 扫描（完成）
- **E2 Catalog v2 构建**：items + craft + cooking + assets（完成）
- **E3 Tuning trace**：链路索引 + 按需加载（完成）
- **E4 Icon pipeline**：静态 icon + 动态回退（完成）

### 数据质量
- **E5 stats 覆盖扩展**：更多组件/属性/方法（进行中）
- **E6 i18n 覆盖扩展**：names/desc/quotes + UI 词条（进行中）
- **E7 质量报告与门禁**：report_hub + quality_gate（完成）

### WebCraft 应用
- **E8 Catalog 列表/检索**：items + indexes（完成）
- **E9 Item 详情与 stats 展示**（完成）
- **E10 i18n UI**：语言切换（完成）
- **E11 Trace UI 按需加载**（完成）
- **E12 交互体验增强**（规划中）
  - 料理探索：食材驱动筛选 + 模拟结果 + 规则可解释
  - 列表密度：表格/卡片切换，中英文/调试 ID 同屏，快捷复制
  - 导航一致：统一 list/detail 框架，支持 URL 状态、键盘/移动端操作
  - 料理食材索引：解析 ingredients/cooking 定义，落盘 cooking_ingredients 标签与来源
  - 探索/模拟入口：百科为主，探索/模拟耦合；排序公式 + 接近可做解释

### 工程化与工具链
- **E13 CLI 统一入口**（完成）
- **E14 任务入口规范**（完成）
- **E15 Snapshot 规范**（完成）

### 机制解析路线
- **E17 静态机制解析（Static Mechanics）**：prefab/component/stats/recipes 等静态机制结构
- **E18 行为图谱解析（Behavior Graph）**：stategraph/brain/event 结构化关系

### 服务器运维
- **E16 DST server 管理**（完成）

## 4. L3 当前任务（Active）

- **T-101**：stats 覆盖扩展（组件属性/方法解析补全）
- **T-102**：i18n 覆盖提升（names/desc/quotes + UI 文案）
- **T-103**：Catalog 质量报告迭代（覆盖率与缺口追踪）
- **T-104**：Cooking ingredient tags 解析与 catalog 落盘（ingredients.lua / cooking.lua）
- **T-105**：Cooking 探索/模拟重做（可做/接近可做 + 解释卡片 + 高密度切换）
- **T-106**：Mechanism index v1（组件解析 + prefab 链路）
- **T-107**：Mechanism SQLite schema v1（links 表 + 统一映射策略）
- **T-108**：Mechanism summary + consistency 校验（JSON/SQLite 对齐）
- **T-109**：Mechanism crosscheck 报告（resource_index 对齐 + 缺口清单）
- **T-112**：Mechanism JSON schema 文件（machine-readable）
- **T-113**：Mechanism build 严格校验开关（--strict）
- **T-114**：SQLite v4 schema 设计（DDL + 索引 + 迁移策略，见 `docs/specs/SQLITE_V4_SPEC.md`）

## 5. 最近完成（摘要）

- wagstaff server 接入，运维模块独立化
- WebCraft UI 模块化：模板迁移至 `apps/webcraft/templates/`，CSS/JS 拆分到 `apps/webcraft/static/`
- Catalog index v1 规范与 WebCraft API 契约补齐
- pyproject 入口统一、bin/installer 清理完成
- 新增耕种机制索引产物与机制报告（farming defs）
- Farming: mechanics 公式摘要补齐 + 轻量模拟 CLI（farming-sim）
- Farming: 混种配比规划算法（季节筛选/营养平衡/水分需求）
- WebCraft: Farming 混种规划工具 UI + API
- 索引清单落盘：新增 `index-manifest` 生成器与 Makefile 入口
- SQLite 产物增加 `db_schema_version=4`，为 v4 结构演进预留标记
- core 收口：`klei_atlas_tex` 迁移至 `core/assets/`，配置加载迁移至 `core/config/`
- 索引全量重建并生成 `wagstaff_index_manifest.json`
- SQLite v4：catalog/mechanism 构建器升级 + WebCraft v4 表优先加载
- mechanism-index 收口：validate/diff 合并为子命令，旧脚本内退
- 静态机制覆盖基准与组件能力地图落盘（static_mechanics_coverage）
- 行为图谱 MVP 索引与数据契约草案完成（behavior_graph_v1）
- CatalogV2: stats 组件默认值回填并标注来源（component_default）
- BehaviorGraph: StateGraph 边补全 + Brain 节点/边启发式解析（mvp+）
- i18n: 新增 descriptions/quotes 索引与 API 端点
- Quality: catalog_quality 增加 stats 来源统计与趋势对比
- WebCraft: Catalog stats 展示数据来源（source/source_component）
- WebCraft: Catalog 详情展示 descriptions/quotes（EN 优先、CN 回退）
- i18n: 语言优先级规则（ID 基础、EN 首选、CN 备选）
- i18n: strings.lua 英文索引 + quotes_meta 记录台词角色来源
- i18n: speech_*.lua 英文描述/台词补齐（EN 优先不回退 CN）

## 6. 下一步建议（短期）

1. 以 stats 解析覆盖为主线，补齐关键组件（equippable/rechargeable/heater 等）
2. i18n 覆盖率提升，补齐 UI 词条并完善多语言元数据
3. 质量报告指标化：新增缺失原因统计与趋势对比
