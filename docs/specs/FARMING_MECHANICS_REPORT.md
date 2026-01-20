# 耕种机制报告 (DST)

本报告整理 DST 耕种系统的核心机制、关键调参与数据源，供模拟/规划系统使用。

## 数据来源

- `scripts/prefabs/farm_plant_defs.lua`：作物定义、季节/营养/湿度偏好、成长与巨型权重
- `scripts/prefabs/farm_plants.lua`：作物成长流程、压力测试与产出逻辑
- `scripts/components/farmplantstress.lua`：压力累计与最终压力等级
- `scripts/components/farming_manager.lua`：土壤湿度/营养循环、季节性杂草生成
- `scripts/prefabs/weed_defs.lua` + `scripts/prefabs/weed_plants.lua`：杂草成长与扩散
- `scripts/prefabs/veggies.lua`：作物种子权重 (randomseed 选择)
- `scripts/prefabs/fertilizer_nutrient_defs.lua`：肥料营养值
- `scripts/tuning.lua`：耕种相关调参

## 种子与杂草清单

### 可种植作物 (14)

`asparagus`、`garlic`、`pumpkin`、`corn`、`onion`、`potato`、`dragonfruit`、`pomegranate`、`eggplant`、`tomato`、`watermelon`、`pepper`、`durian`、`carrot`

对应种子：`{plant}_seeds`，详见 `farm_plant_defs.lua` 与 `veggies.lua`。

### 原始种子

`seeds` → `farm_plant_randomseed`，随机生成作物或杂草；详见 `seeds.lua`、`farm_plants.lua`。

### 农田杂草

`weed_forgetmelots`、`weed_tillweed`、`weed_firenettle`、`weed_ivy`；详见 `weed_defs.lua`、`weed_plants.lua`。

## 成长阶段与时间

作物阶段：`seed → sprout → small → med → full → rotten`

`farm_plant_defs.lua` 中 `MakeGrowTimes()` 定义：

- 发芽期：`seed = [germ_min, germ_max]`
- 生长期：`sprout/small/med` 由 `full_grow_min/max` 按 0.5/0.3/0.2 分摊
- 成熟腐烂：`full = 4 * TOTAL_DAY_TIME`
- 巨型腐烂：`oversized = 6 * TOTAL_DAY_TIME`
- 再生：`regrow = [4, 5] * TOTAL_DAY_TIME`

季节加速：若为作物偏好季节，发芽与生长期 *0.5（`farm_plants.lua`）。

## 压力系统

压力类别（`farm_plants.lua`）：

- `killjoys`：半径内“杀手”植物数量 > `FARM_PLANT_KILLJOY_TOLERANCE`
- `family`：同类数量 < `FARM_PLANT_SAME_FAMILY_MIN`（含自己）
- `overcrowding`：同 tile 作物数量 > `FARM_PANT_OVERCROWDING_MAX_PLANTS`
- `season`：非偏好季节
- `moisture`：湿度低于 `FARM_PLANT_DROUGHT_TOLERANCE`
- `nutrients`：营养不足
- `happiness`：未被照料 (tend)

最终压力等级（`farmplantstress.lua`）：

- `NONE`：累计压力点 ≤ 1
- `LOW`：≤ 6
- `MODERATE`：≤ 11
- `HIGH`：其他

产出影响（`farm_plants.lua`）：

- `NONE/LOW`：1 作物 + 2 种子
- `MODERATE`：1 作物 + 1 种子
- `HIGH`：仅 1 作物
- `NONE` 且允许巨型：可能生成巨型作物

## 营养系统

土壤营养三通道（index 1/2/3），每阶段成长结算一次（`farming_manager.lua`）：

- 消耗：按 `nutrient_consumption` 扣减
- 恢复：把消耗总量平均分配到“未消耗”的通道
- 不足：当前阶段压力直接成立，补肥仅影响后续阶段

关键调参：

- `FARM_PLANT_CONSUME_NUTRIENT_LOW/MED/HIGH`
- `STARTING_NUTRIENTS_MIN/MAX`
- 肥料营养值见 `fertilizer_nutrient_defs.lua`

## 湿度系统

`farming_manager.lua` 每 `SOIL_MOISTURE_UPDATE_TIME` 更新：

```
soil_moisture += dt * (rain_rate * SOIL_RAIN_MOD or temp_dry_rate + sum(drink_rate))
soil_moisture = clamp(soil_moisture, world_wetness, SOIL_MAX_MOISTURE_VALUE)
```

作物吸水率由 `farm_plant_defs.lua` 定义：`FARM_PLANT_DRINK_LOW/MED/HIGH`。

## 原始种子与杂草生成

`farm_plants.lua`：

- `FARM_PLANT_RANDOMSEED_WEED_CHANCE`：randomseed 生成杂草概率
- 否则基于 `VEGGIES.seed_weight` 抽取作物
- 偏好季节权重乘 `SEED_WEIGHT_SEASON_MOD`

`farming_manager.lua`：

- `SEASONAL_WEED_SPAWN_CAHNCE`：季节性杂草生成概率（秋/春）
- 生成窗口 = 当季剩余天数 * 0.25

## 杂草扩散

`weed_defs.lua` 定义扩散窗口与距离参数：

- `spread.stage`：触发扩散的生长阶段
- `time_min/time_var`：扩散计时
- `tilled_dist`：优先寻找犁地土
- `ground_dist` / `ground_dist_var`：地面扩散半径
- `tooclose_dist`：同类最小距离

`weed_plants.lua` 执行扩散，成功后延迟倍增。

## 数据产物

新增耕种机制索引产物：

- `data/index/wagstaff_farming_defs_v1.json`
- 由 `devtools/build_farming_defs.py` 构建
- 内容包含 `tuning`、`seed_weights`、`plants`、`weeds`、`fertilizers` 与统计信息
