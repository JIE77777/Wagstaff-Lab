# Wagstaff Worldgen Index v1 规范草案

目标：为 DST 地图生成机制提供“可查询、可解释”的最小索引，覆盖 preset → taskset → task → room/layout 的结构链路。

## 1. 产物与版本

- JSON: `data/index/wagstaff_worldgen_index_v1.json`
- SQLite: `data/index/wagstaff_worldgen_index_v1.sqlite`
- schema_version: 1
- JSON schema: `docs/specs/worldgen_index_v1.schema.json`
- SQLite 结构版本通过 `meta.db_schema_version` 标记（对齐 v4）

## 2. 数据来源（脚本）

- 入口与生成流程：`scripts/worldgen_main.lua` / `scripts/map/forest_map.lua` / `scripts/map/storygen.lua`
- presets/levels：`scripts/map/levels.lua` + `scripts/map/levels/*.lua`
- tasksets：`scripts/map/tasksets.lua` + `scripts/map/tasksets/*.lua`
- tasks：`scripts/map/tasks.lua` + `scripts/map/tasks/*.lua`
- rooms：`scripts/map/rooms.lua` + `scripts/map/rooms/**`
- layouts：`scripts/map/layouts.lua` + `scripts/map/static_layouts/**`
- start locations：`scripts/map/startlocations.lua`
- settings/options：`scripts/map/customize.lua` / `scripts/map/settings.lua`
- overrides → tuning：`scripts/worldsettings_overrides.lua`

## 3. JSON 顶层结构

```yaml
schema_version: 1
meta: {schema, project_version, index_version, generated, tool, sources, scripts_sha256_12, ...}
counts:
  settings_presets_total: int
  worldgen_presets_total: int
  tasksets_total: int
  tasks_total: int
  rooms_total: int
  layouts_total: int
  set_pieces_total: int
  start_locations_total: int
presets:
  settings: {preset_id: SettingsPreset}
  worldgen: {preset_id: WorldgenPreset}
tasksets: {taskset_id: TaskSet}
tasks: {task_id: Task}
rooms: {room_id: Room}
layouts:
  static: {layout_id: Layout}   # 来自 static_layouts
  dynamic: {layout_id: Layout}  # 来自 layouts.lua
start_locations: {id: StartLocation}
set_pieces: {id: SetPiece}
options:
  worldsettings: {option_id: OptionDef}
  worldgen: {option_id: OptionDef}
links:
  preset_taskset: [Link, ...]
  taskset_task: [Link, ...]
  task_room: [Link, ...]
  room_layout: [Link, ...]
  preset_set_piece: [Link, ...]
  taskset_set_piece: [Link, ...]
```

### 3.1 SettingsPreset

```yaml
type: "settings_preset"
id: "SURVIVAL_TOGETHER"
name: "..."
desc: "..."
location: "forest"
version: 2
overrides: { ... }   # worldsettings
playstyle: "default" # 可选
raw: { ... }         # 原始结构（可选）
```

### 3.2 WorldgenPreset

```yaml
type: "worldgen_preset"
id: "SURVIVAL_TOGETHER"
name: "..."
desc: "..."
location: "forest"
version: 4
task_set: "default"
start_location: "default"
required_setpieces: ["Sculptures_1", "Maxwell5", ...]
random_set_pieces: ["Chessy_1", ...]
numrandom_set_pieces: 4
overrides: { ... }   # worldgen overrides
raw: { ... }
```

### 3.3 TaskSet

```yaml
type: "taskset"
id: "default"
name: "..."
location: "forest"
tasks: ["Make a pick", ...]
optionaltasks: ["Befriend the pigs", ...]
numoptionaltasks: 5
valid_start_tasks: ["Make a pick"]
required_prefabs: ["gravestone", ...]
set_pieces: {ResurrectionStone: {count: 2, tasks:[...]} , ...}
ocean_population: ["OceanCoastal", ...]
raw: { ... }
```

### 3.4 Task

```yaml
type: "task"
id: "Make a pick"
locks: ["NONE"]
keys_given: ["PICKAXE"]
room_bg: "GRASS"
background_room: "BGGrass"
room_choices: {Forest: 1, SpiderCon: 3, ...}
colour: {r: 0, g: 1, b: 0, a: 1}
raw: { ... }
```

### 3.5 Room

```yaml
type: "room"
id: "BGGrass"
value: "WORLD_TILES.GRASS"
tags: ["ExitPiece", "Chester_Eyebone", ...]
contents:
  distributepercent: 0.275
  distributeprefabs: {grass: 0.2, tree: {weight:0.3, prefabs:[...]}, ...}
  countprefabs: {spawnpoint_multiplayer: 1, ...}
  prefabdata: {evergreen: {burnt: true}}
raw: { ... }
```

### 3.6 Layout / SetPiece

```yaml
type: "layout"
id: "Sculptures_1"
source: "static_layouts/..."
layout_type: "STATIC | CIRCLE_EDGE | CIRCLE_RANDOM | CUSTOM"
defs: { ... }
layout: { ... }
count: { ... }
scale: 1.2
add_topology: {room_id: "...", tags: [...] } # 可选
areas: { ... } # 可选
raw: { ... }
```

### 3.7 StartLocation

```yaml
type: "start_location"
id: "default"
start_setpeice: "DefaultStart"
start_node: "Forest_Start"
raw: { ... }
```

### 3.8 OptionDef

```yaml
type: "option"
id: "world_size"
group: "misc"
default: "default"
options: [{text: "...", data: "small"}, ...]
source: "worldgen | worldsettings"
```

### 3.9 Link

```yaml
source: "preset | taskset | task | room"
source_id: "..."
target: "taskset | task | room | layout | set_piece"
target_id: "..."
relation: "uses | optional | random | required | bg | layout"
```

## 4. SQLite 结构（建议）

核心表：

- `meta`（schema_version / db_schema_version / build meta）
- `settings_presets(id, name, desc, location, version, overrides_json, raw_json)`
- `worldgen_presets(id, name, desc, location, version, task_set, start_location, required_setpieces_json, random_set_pieces_json, numrandom_set_pieces, overrides_json, raw_json)`
- `tasksets(id, name, location, tasks_json, optionaltasks_json, numoptionaltasks, valid_start_tasks_json, required_prefabs_json, set_pieces_json, ocean_population_json, raw_json)`
- `tasks(id, locks_json, keys_given_json, room_bg, background_room, room_choices_json, colour_json, raw_json)`
- `rooms(id, value, tags_json, contents_json, raw_json)`
- `layouts(id, source, layout_type, defs_json, layout_json, count_json, scale, add_topology_json, areas_json, raw_json)`
- `set_pieces(id, layout_id, source, raw_json)`（若静态布局与 set piece 合并，可省略）
- `start_locations(id, start_setpeice, start_node, raw_json)`
- `options(id, group_id, default_value, options_json, source)`

关系表：

- `preset_tasksets(preset_id, taskset_id, relation)`（relation=worldgen|settings）
- `taskset_tasks(taskset_id, task_id, relation)`（relation=main|optional|valid_start）
- `task_rooms(task_id, room_id, weight)`
- `room_layouts(room_id, layout_id, relation)`
- `preset_set_pieces(preset_id, set_piece_id, relation)`
- `taskset_set_pieces(taskset_id, set_piece_id, relation)`

## 5. 解析计划（v1）

1) **入口枚举**：扫描 `scripts/map/` 与 `scripts/worldgen_main.lua`，建立 worldgen 文件清单。
2) **Presets**：
   - 解析 `AddLevel` / `AddWorldGenLevel` / `AddSettingsPreset`。
   - 按 location/leveltype 分组，保留原始 overrides。
3) **TaskSets / Tasks**：
   - 解析 `AddTaskSet` 与 `AddTask`。
   - 记录 `tasks/optionaltasks/room_choices` 与 set_pieces 关系。
4) **Rooms**：
   - 解析 `AddRoom` 的 `value/tags/contents`。
   - 动态 `function` 值落 `raw/unknown`，避免丢失。
5) **Layouts / SetPieces**：
   - 解析 `static_layouts/**` 与 `layouts.lua`。
   - 建立 `set_piece_id → layout_id` 映射。
6) **StartLocations**：
   - 解析 `startlocations.lua` 并处理 `table` 选择结构。
7) **Options**：
   - 解析 `customize.lua` 的 worldsettings/worldgen options。
8) **Link 与校验**：
   - 生成 links + 缺口清单（未解析的 room/layout/taskset 引用）。
   - 输出统计 counts 与缺口报告。

## 6. 一致性与校验

- `preset.task_set` 必须存在于 `tasksets`（缺失则记录）。
- `task.room_choices` 引用必须存在于 `rooms`。
- `set_pieces` 引用必须在 `layouts/static` 内可解析。
- counts 与 links 数量匹配（links 仅统计已解析项）。

## 7. 兼容与演进

- v1 仅记录配置与规则，不模拟 WorldSim 实际落点。
- v2 可加入：
  - 运行时 worldsim 产物（topology/tile map 摘要）
  - override → tuning 影响分析
  - worldgen 与 behavior_graph 的跨索引链接
- 若统一到 mechanism index，可新增 `worldgen_*` 表并更新 `db_schema_version`。
