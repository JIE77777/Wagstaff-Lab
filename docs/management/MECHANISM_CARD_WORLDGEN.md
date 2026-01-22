# 机制卡片：DST 地图生成（Worldgen / Mapgen）

Mechanism:
- DST Worldgen / Mapgen（从 preset → taskset → task → room/layout → topology → entities）

Purpose:
- 结构化理解 DST 地图生成的配置与组合规则，形成可查询索引与解析规则，支持后续可视化/模拟/解释输出。

Primary files (scripts.zip):
- `scripts/worldgen_main.lua`（入口：读取 GEN_PARAMETERS + Level 构建）
- `scripts/map/forest_map.lua`（核心生成管线：storygen + WorldSim + tiles + entities）
- `scripts/map/storygen.lua`（任务图与拓扑生成）
- `scripts/map/levels.lua` + `scripts/map/levels/*.lua`（level preset + worldgen preset）
- `scripts/map/tasksets.lua` + `scripts/map/tasksets/*.lua`（taskset 定义）
- `scripts/map/tasks.lua` + `scripts/map/tasks/*.lua`（task 定义）
- `scripts/map/rooms.lua` + `scripts/map/rooms/**`（room 定义）
- `scripts/map/startlocations.lua`（起点规则）
- `scripts/map/layouts.lua`（动态 layout 模板）
- `scripts/map/static_layouts/**`（set piece / static layout）
- `scripts/map/terrain.lua`（地形过滤与 room 访问入口）
- `scripts/map/customize.lua`（worldgen/settings 选项清单）
- `scripts/map/settings.lua`（SettingsPreset 结构）
- `scripts/worldsettings_overrides.lua`（override → tuning 逻辑）
- `scripts/worldentities.lua`（world entities 注入）
- 额外世界生成：`scripts/map/archive_worldgen.lua` / `waterlog_worldgen.lua` / `monkeyisland_worldgen.lua`

Related components/data:
- `TUNING` / `STRINGS` / `constants` / `tiledefs` / `tilegroups`
- `worldgenoverride.lua`（由工具生成的 override 文件，包含 presets 与 overrides）
- `data/levels/`（worldgen 运行时产物）

Key functions and rules:
- `worldgen_main.lua`
  - `LoadParametersAndGenerate()` → `GenerateNew()` → `forest_map.Generate(...)`
  - `Level:ChooseTasks()` / `AddSetPeices()` / `Level:ChooseSetPieces()`
- `forest_map.Generate(...)`
  - 根据 overrides 生成 `story_gen_params`
  - `BuildStory(...)` → 生成 topology + tags
  - WorldSim: Voronoi → Commit → Connectivity → Roads → TileMap
  - 编码 topology + 生成 entities（prefab/布局）
- `storygen.lua`
  - `GenerateNodesFromTasks()` / `AddBGNodes()` / `InsertAdditionalSetPieces()` / `ProcessOceanContent()`
- `tasks/*.lua`
  - `Task(room_choices, room_bg, background_room, locks/keys)`
- `rooms/**/*.lua`
  - `Room(value, tags, contents)`：`distributepercent` / `distributeprefabs` / `countprefabs` / `static_layouts`
- `layouts.lua` + `static_layouts/**`
  - layout 模板 / set pieces（静态布局）

Output design (fields):
- Must-have:
  - `settings_presets` / `worldgen_presets`
  - `tasksets` / `tasks` / `rooms`
  - `layouts` / `set_pieces`
  - `start_locations`
  - Links: preset→taskset, taskset→task, task→room, room→layout/setpiece
- Nice-to-have:
  - override 选项元数据（group/options/default）
  - terrain filter 映射（prefab → disallow tiles）
  - worldsettings override → tuning 映射摘要
  - ocean / special worldgen pipelines（archive/waterlog/monkeyisland）

Extraction rules:
1) `AddLevel` / `AddWorldGenLevel` / `AddSettingsPreset` 抽取 presets（原始 overrides 保留）
2) `AddTaskSet` 抽取 taskset（tasks/optionaltasks/set_pieces/ocean_population）
3) `AddTask` 抽取 task（room_choices / room_bg / background_room / locks/keys）
4) `AddRoom` 抽取 room（value/tags/contents；函数值保留 raw）
5) `static_layouts/**` 与 `layouts.lua` 抽取 layout/set piece 定义
6) `startlocations.lua` 抽取起点配置
7) 生成 links + 缺口清单（未解析的 layout/setpiece/task/room 引用）

Known difficulties:
- room/layout 中大量 `function` 与 `math.random` 动态逻辑
- mod hooks（AddMod*）与平台分支（console/ps4）
- worldsettings overrides 与 tuning 关系复杂
- WorldSim 输出为运行时数据，非静态解析可得

Gaps and impact:
- 不模拟 WorldSim/实体真实落点，索引仅覆盖“配置与规则”
- 复杂 layout 或动态 prefab 组合仅能保留 raw

Validation samples (>= 10):
- `map/levels/forest.lua`, `map/levels/caves.lua`
- `map/tasksets/forest.lua`, `map/tasksets/caves.lua`
- `map/tasks/forest.lua`, `map/tasks/ruins.lua`
- `map/rooms/forest/terrain_grass.lua`, `map/rooms/cave/rocky.lua`
- `map/layouts.lua`, `map/static_layouts/rooms/atrium_end/atrium_end.lua`
- `map/startlocations.lua`
- `worldsettings_overrides.lua`

Done criteria:
- Presets/TaskSets/Tasks/Rooms/Layouts 解析覆盖率 >= 0.95
- 样本校验 >= 10 个，字段与引用链路一致
- 未识别字段落 `raw/unknown` 并记录缺口清单
