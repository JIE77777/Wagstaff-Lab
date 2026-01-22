# DST Worldgen 机制讨论笔记

目的：整理世界生成（worldgen/mapgen）机制要点，便于后续复盘与工具化。

## 1. 种子（Seed）在何时引入

- 入口脚本：`scripts/worldgen_main.lua`
- `SetWorldGenSeed(SEED)` 在 worldgen 启动阶段执行，早于任务/房间/布局选择。
- `SEED` 若未传入，则使用 `os.time()` 反转取前 6 位作为种子。
- 脚本里会在加载 mods 前后各执行一次 `SetWorldGenSeed`，最终保证随机序列统一锁定。

结论：**种子在生成地图之前就被确定，并贯穿整个 worldgen 随机流程。**

## 2. Worldgen 分阶段流程（可作为断点）

按脚本实际顺序划分：

S0 参数与种子  
- 入口：`worldgen_main.lua`  
- 产物：确定随机序列

S1 载入配置 / Level 构建  
- 加载 `levels/tasksets/tasks/rooms/startlocations`  
- 产物：完整 level preset + overrides

S2 任务与 set pieces 选择  
- `Level:ChooseTasks()` / `AddSetPeices()` / `Level:ChooseSetPieces()`  
- 产物：任务列表、set piece 清单（必刷/随机）

S3 Story/Topology 逻辑图  
- `map/storygen.lua` → `BuildStory`  
- 产物：节点/边/标签（结构拓扑）

S4 WorldSim 地形生成  
- `forest_map.Generate` 内部：Voronoi → Commit → ConvertToTileMap → Connectivity → Roads  
- 产物：真实地形 tilemap

S5 房间填充与布局放置  
- room 内容分布、layout/set piece 放置  
- 产物：关键资源/营地的实际位置

S6 编码与保存  
- `SaveEncode` 生成 `savedata.map` / `savedata.ents`  
- 产物：可持久化的世界数据

S7 worldentities 注入  
- `worldentities.lua`  
- 产物：补齐全局实体

## 3. 轻量模拟 vs 精确预览

轻量模拟（不依赖 WorldSim）：
- 能给结构层结论：preset/taskset/task/room/set piece
- 能给“是否出现/数量范围/权重”级别判断
- 不能给位置、距离与实际地形形态

精确预览（依赖 WorldSim）：
- 必须启动引擎运行时（dedicated server 的 worldgen 进程即可，无需客户端 UI）
- 可输出 tilemap + entities 坐标，用于地图预览

结论：**结构层可离线；几何层必须跑 WorldSim。**

## 4. 是否可以单独调用 worldgen 进程

可以，但必须带引擎：
- worldgen 大量调用 `WorldSim:*`，不是纯 Lua/纯 Python 可替代
- 可以 headless 跑 dedicated server 的 worldgen 阶段，用于预览或导出

## 5. 断点性价比（建议）

高性价比断点：
- **S2（任务/SetPiece 选择后）**：最便宜，适合快速筛选“值不值得开档”
- **S3（Topology 后）**：能看到结构形态（分支/环路/岛屿倾向）

低性价比断点：
- **S5/S6**：成本接近完整 worldgen，但能得到精确位置与预览能力

## 6. 示例：海象营地（结构层）

- 房间定义：`scripts/map/rooms/forest/walrus.lua`  
  - `WalrusHut_*` 房间含 `walrus_camp = 1`
- 任务引用：`scripts/map/tasks/forest.lua` 中多个任务引用 `WalrusHut_*`
- 是否出现取决于 taskset 与任务抽取

结构结论：**默认 preset 下“可能有海象营地，但不保证”；精确位置必须跑 WorldSim。**

## 7. 可产出清单（按阶段）

- S2：task/taskset/rooms/set pieces 清单（是否出现 + 数量范围）
- S3：topology graph（nodes/edges/tags）
- S5/S6：tilemap + entities 坐标（用于渲染预览）

## 8. 建议的工具化方向

- `worldgen-precheck`：S2/S3 结构级输出（快速筛档）
- `worldgen-preview`：S5/S6 真实地图预览（坐标级）
- `WORLDGEN_STOP_STAGE`：统一断点开关，输出对应阶段 JSON
