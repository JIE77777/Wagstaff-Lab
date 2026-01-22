# Worldgen 解析工具设计文档（结构解析 + S3 拓扑骨架）

目标：在不依赖 WorldSim 的前提下，完成 **轻量结构解析** 与 **S3 拓扑骨架图** 的产出，形成可查询索引与结构可视化能力。

本文遵循 `docs/guides/DEV_GUIDE.md` 的分层与产物规范。

---

## 1. 范围与阶段

### 1.1 目标（本阶段完成）
- 解析 worldgen 静态结构：preset → taskset → task → room → layout/setpiece。
- 生成 S3 拓扑骨架（nodes/edges/tags），并输出结构化 JSON + 可视化 DOT。
- 产出 `wagstaff_worldgen_index_v1.json`（结构索引）。

### 1.2 不在本阶段
- WorldSim 运行时地图生成（S4+）与真实地图预览。
- tilemap 解码与实体坐标渲染。

---

## 2. 分层架构（遵循 DEV_GUIDE）

### 2.1 core/（解析与模型）

新增建议目录（保持最小分级）：

```
core/worldgen/
  __init__.py
  models.py            # 数据模型：Preset/TaskSet/Task/Room/Layout/Topology
  extractors/
    __init__.py
    presets.py         # AddLevel/AddWorldGenLevel/AddSettingsPreset
    tasksets.py        # AddTaskSet
    tasks.py           # AddTask
    rooms.py           # AddRoom
    layouts.py         # layouts.lua + static_layouts/*
    startlocations.py  # startlocations.lua
  topology/
    __init__.py
    graph_builder.py   # S3 拓扑模型构建
    graph_metrics.py   # 分支/环路/岛屿倾向指标
  render/
    __init__.py
    topology_dot.py    # DOT 输出（骨架图）
    topology_json.py   # JSON 输出（骨架图）
```

说明：
- 解析层使用现有 `core/lua` 工具（`LuaCallExtractor`、`split`、`match`）。
- 模型不引入外部依赖，保持纯 Python 结构。

### 2.2 core/indexers/

新增：

```
core/indexers/worldgen_index.py
```

职责：
- 组装解析结果，输出 JSON（+后续 SQLite）。
- 构建 meta（引用 `core.schemas.meta`）。

### 2.3 devtools/（流程入口）

新增：

```
devtools/build_worldgen_index.py   # 生成结构索引
devtools/worldgen_topology.py      # 生成 S3 骨架图 JSON/DOT + 指标报告
```

### 2.4 apps/cli（统一入口）

新增命令：

```
apps/cli/commands/worldgen.py
```

子命令（仅结构层）：
- `wagstaff worldgen build`：结构索引
- `wagstaff worldgen topo`：S3 骨架图

---

## 3. 数据模型与索引输出

### 3.1 模型要点
- SettingsPreset / WorldgenPreset（overrides 保留）
- TaskSet / Task / Room / Layout
- TopologyGraph（nodes/edges/tags + region）

### 3.2 索引规范
对齐：`docs/specs/WORLDGEN_INDEX_SPEC.md`

产物：
- `data/index/wagstaff_worldgen_index_v1.json`
- `data/reports/worldgen_topology_report.json`
- `data/reports/worldgen_topology_graph.dot`

---

## 4. 解析管线（轻量结构）

### Step A: 文件枚举
输入来源（scripts.zip 或脚本目录）：
- `map/levels.lua`, `map/levels/*.lua`
- `map/tasksets.lua`, `map/tasksets/*.lua`
- `map/tasks.lua`, `map/tasks/*.lua`
- `map/rooms.lua`, `map/rooms/**`
- `map/layouts.lua`, `map/static_layouts/**`
- `map/startlocations.lua`

### Step B: Call 提取
使用 `LuaCallExtractor` 匹配：
- `AddLevel` / `AddWorldGenLevel` / `AddSettingsPreset`
- `AddTaskSet` / `AddTask` / `AddRoom`
- Layout/static layout 注册结构（视具体文件结构解析）

### Step C: 结构归一化
- 所有 ID 统一 lower/trim
- 可执行函数值保留为 `raw`
- 内容结构保留原始文本片段便于追溯

### Step D: Links & 校验
生成链接：
- preset → taskset
- taskset → task
- task → room
- room → layout/setpiece

校验缺口：
- 引用未解析的 task/room/layout
- 统计缺口清单输出到 report

---

## 5. S3 拓扑骨架图

### 5.1 输入
- taskset/task/room 的结构索引
- storygen 中拓扑节点定义（可通过规则映射到任务集/房间层级）

### 5.2 输出
Topology JSON:
```
{
  "nodes": [{ "id": "...", "kind": "task|room|region", "tags": [], "region": "mainland" }],
  "edges": [{ "source": "...", "target": "...", "relation": "connects" }],
  "meta": { "branching": "...", "loop": "...", "islands": "...", "seed": "..." }
}
```

DOT 输出：
- 仅表达骨架图结构，不表示真实地形。

### 5.3 结构指标

- 分支度（avg degree）
- 环路数量（cycle count）
- 独立区域数量（components）
- 起点节点所在区域

---

## 6. 骨架 → 完成（阶段计划）

### Phase 0: 骨架
- 创建包结构与空模块
- 确定数据模型与 schema 映射

### Phase 1: 结构解析 MVP
- presets/tasksets/tasks/rooms 解析
- 输出 index JSON

### Phase 2: Layout & set piece
- layouts.lua + static_layouts 抽取
- room → layout/setpiece 链接

### Phase 3: S3 拓扑骨架
- topology graph 输出
- DOT/JSON + 指标报告

完成标准：
- 结构索引覆盖率 ≥ 0.90
- 拓扑骨架能稳定输出 nodes/edges/tags
- 缺口清单可追溯

---

## 7. 子目录分级策略（复杂度控制）

建议策略：
- **最小分级**优先：同一领域文件数 > 5 才拆 `extractors/` 或 `topology/`。
- **不超过两级**：`core/worldgen/*` + `core/worldgen/extractors/*` 足够。
- **功能分域优先**：解析（extractors）与图结构（topology）分离。

本阶段建议仅新增 `core/worldgen/` 一级包，按需再拆子模块。

---

## 8. 验证与质量

- 结构索引：
  - preset/taskset/task/room/link 完整性
  - 引用缺失统计
- 拓扑骨架：
  - nodes/edges 可视化验证（DOT）
  - 与 taskset 结构一致性检查

---

## 9. 文档关联

- 机制卡：`docs/management/MECHANISM_CARD_WORLDGEN.md`
- 索引规范：`docs/specs/WORLDGEN_INDEX_SPEC.md`
- 机制路线：`docs/management/PROJECT_MANAGEMENT.md` (E19)
