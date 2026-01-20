# Wagstaff-Lab vNext 重构规划（破兼容版）

目标：清理历史包袱，重建 core 架构与索引流水线，为下一代能力打底（机制解析、模拟、分析工具、可视化、服务器管理增强）。

## 0. 背景与约束

- 版本兼容性非重点，可进行破坏性重构。
- 当前痛点：core 过于耦合（解析/领域逻辑/索引混杂），索引构建链路难复用，机制解析与模拟缺乏统一入口。
- vNext 必须提供明确的“机制解析 → 索引 → 分析 → 可视化”的链路。

## 0.1 已确认方向

- **机制解析优先级**：组件解析优先（Components > StateGraph > Brain）。
- **产物形态**：JSON 与 SQLite 同步落盘。
- **版本策略**：v4 破兼容重构。
- **旧 analyzer.py**：彻底移除，不保留兼容层。
- **应用层节奏**：应用层慢慢做，core 重构优先。
- **WebCraft UI**：保留 Cooking 模拟工具；Catalog/Craft/Cooking 图鉴页重做。
- **索引引用方式**：统一 id（以 prefab 为核心）+ 映射表兜底。

## 1. 重构原则（抛弃历史包袱）

- 允许移除旧 API 与旧文件结构，不做兼容层“补丁”。
- 以模块职责为中心，避免单文件巨型模块。
- 以数据契约驱动索引与工具；一切产物可验证、可追溯。
- 解析与索引分离：解析做“事实抽取”，索引做“结构化输出”。
- 抽离配置/IO：engine 专注挂载与读取；解析/索引不直接读磁盘。

## 2. vNext 目标产物

- **catalog v3**：更细粒度的物品/机制索引，覆盖组件、状态机、掉落、行为、技能、资源链路。
- **mechanism index**：DST 机制解析产物（组件属性/方法、状态机、脑图、事件流、配方规则）。
- **component index**：组件定义与接口索引（字段/方法/默认值/事件）。
- **simulation index（轻量）**：以种植为主的简化模拟输入输出与参数表。
- **analysis reports**：覆盖率、机制差异、脚本演进对比等。
- **storage**：JSON 与 SQLite 同步落盘，机制索引与 catalog 同步支持查询。
  - JSON 主键统一以 prefab id 为核心，附 `links` 映射表兜底。
  - Mechanism index 规范：`docs/specs/MECHANISM_INDEX_SPEC.md`

## 3. 目标架构蓝图

```
core/
  engine/           # scripts 挂载、读文件、缓存、索引源
  lua/              # lexer/split/match/call-extract/table-parse
  parsers/          # prefab/loot/widget/strings/cooking/sg/brain
  indexers/         # resource/catalog/mechanism/simulation/i18n
  schemas/          # 数据契约 + meta + validators
  sim/              # farming/cooking/未来战斗/AI 模拟
  assets/           # atlas/tex/png 解析与转换
  config/           # 配置加载、路径解析、环境探测
  tools/            # 低耦合工具与跨索引共享逻辑
```

依赖方向：
- `parsers` 仅依赖 `lua` + 纯数据结构。
- `indexers` 依赖 `engine` + `parsers` + `schemas`。
- `apps` 与 `devtools` 仅通过 `core/indexers` + `core/schemas`。

## 4. 核心能力增强方向

### 4.1 DST 机制解析

- **组件解析优先**：组件 API 解析先落盘（属性、方法、数值推导，含 TUNING 链路）。
- 状态机解析：StateGraph、事件流与状态迁移图。
- AI/Brain 解析：行为树/脑图结构与条件。
- 资源链路：prefab → 组件 → 掉落 → 产物 → 配方。
  - 统一输出 `links`（source/target/id）用于跨索引 join。

### 4.2 模拟系统（轻量：种植优先）

- 种植模拟：提供“输入参数 → 结论”简化模型（生长时间/营养/水分/季节/肥料）。
- 烹饪模拟：保留规则解释与接近可做输出，不追求重型 UI。
- 输出标准化：模拟输入/输出 schema，为 CLI/报告优先，UI 后置。

### 4.3 分析工具与可视化

- CLI 分析工具：差异报告、机制覆盖率、解析失败样本。
- 可视化系统：机制图谱、状态机图、配方链路图、模拟参数面板。
- 报告模板统一化，便于快照与持续迭代。

### 4.4 服务器管理增强

- 统一命令与任务调度（备份/恢复/巡检/滚动更新）。
- 运行健康与日志聚合，支持结构化输出。
- 与数据分析层解耦，但共享同一配置与日志规范。

### 4.5 存储与查询（SQLite vNext）

- JSON 与 SQLite 同步落盘，保证产物一致性。
- SQLite 结构向“机制查询”优化，采用**中等粒度**拆表：
  - 关系表：`components` / `component_fields` / `component_methods`
  - 状态机：`stategraphs` / `stategraph_states` / `stategraph_events` / `stategraph_edges`
  - AI：`brains` / `brain_nodes` / `brain_edges`
  - 映射：`prefab_components` / `prefab_links`
- 同时保留 `raw_json` 字段或附表，保证解析原貌可追溯。
- 统一映射表：`links(source, source_id, target, target_id)` 作为跨索引连接入口。

## 5. 分阶段里程碑（建议）

### Phase A: Core 拆分与基础迁移
- 拆分 `core/analyzer.py` 为 `core/lua` + `core/parsers/*`。
- `core/engine` 专注挂载/IO/缓存，不承担解析与索引。
- 引入 `schemas/validators`，建立最小校验链路。
- 旧 `core/analyzer.py` 彻底移除，不保留兼容层。

交付标准：
- 旧模块依赖清除 80%+。
- `engine` 无领域逻辑，索引器只做组合。

### Phase B: 索引流水线重建
- 建立“step-based pipeline”（resource → catalog → mechanism → simulation → reports）。
- 缓存与增量构建统一到 `data/index/.build_cache.json`。
- vNext schemas 定义并在 indexers 输出时校验。
- JSON 与 SQLite 同步落盘，建立一致性校验。
  - 机制索引中 `links` 与 SQLite `links` 表保持一致。

交付标准：
- 每个 indexer 有清晰输入/输出契约。
- 可独立复用与单测。

### Phase C: 机制解析落盘
- 组件解析与索引产物优先落盘（component index + prefab 组件映射）。
- StateGraph/Brain 解析器与索引产物落盘。
- 组件方法/属性解析覆盖率提升（与 TUNING 统一追踪）。

交付标准：
- 机制索引产物可被 Web/CLI 查询。

### Phase D: 种植模拟与机制工具
- farming simulation 轻量化落盘，提供可解释输出（CLI/报告优先）。
- 机制/模拟报告工具（差异/覆盖/异常样本）。

交付标准：
- 种植模拟可驱动 UI 与 CLI。

### Phase E: 可视化与服务器管理增强
- 机制可视化页面落地（图谱/状态机/链路）。
- server 管理扩展到调度/巡检与结构化日志。

交付标准：
- 可视化系统与 server 工具进入主入口。

## 6. 迁移与清理策略

- 移除旧 `core/analyzer.py` 巨型模块，拆分为独立目录；不保留兼容层。
- `core/indexers` 内部依赖改为 `parsers` 输出结构，不直接解析 Lua。
- 将 `klei_atlas_tex.py` 迁移到 `core/assets/`，统一图像处理入口。
- 旧 CLI/Devtools 入口保留最小桥接，逐步迁移到新 pipeline。

## 7. 文档与归档策略

- 已完成的规划文档移入 `docs/archived/`。
- 总结性文档保留在 `docs/management/` 与 `docs/specs/`。
- vNext 计划与架构图作为新的主入口之一。

## 8. 质量与验证

- 每个 indexer 有最小测试用例（输入样本 + 输出快照）。
- 增量构建一致性检查（hash/size/field coverage）。
- 机制解析失败样本收敛为可复现的 bug 集合。

## 9. 风险与假设

- 破兼容会导致上层短期不可用，需要短暂冻结期。
- 机制解析覆盖率不足会影响可视化展示，需要逐步补齐。

## 10. 讨论点（请确认）

暂无新增讨论点。
