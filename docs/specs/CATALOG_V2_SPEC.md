# Wagstaff Catalog v2 规范草案

目标：对 DST 做“全面理解与展示”，形成稳定可迁移的索引产物。

说明：本文件仅描述**数据/接口契约**；进度与迁移状态见 `docs/management/PROJECT_MANAGEMENT.md`。
vNext 破兼容重构规划见 `docs/management/VNEXT_REFACTOR_PLAN.md`。

## 1. 总体原则

- **全物品覆盖**：以 prefab 为基础实体，覆盖建筑/生物/角色/物品（不含皮肤）。
- **数据层不含语言**：名称/描述在独立 i18n index 中维护。
- **可迁移**：结构接近“可归一化表”，便于未来迁移到 SQLite/Parquet。
- **可追溯**：所有重要字段需要保留来源与构建元信息。
- **可裁剪**：可按需输出链路（trace）与结果（value）。

## 2. 产物目录建议

- `data/index/wagstaff_resource_index_v1.json`  
  原始资源索引（scripts + prefabs + data + bundles）。
- `data/index/wagstaff_catalog_v2.json`  
  主 Catalog（items + recipes + cooking + assets + tuning）。
- `data/index/wagstaff_catalog_v2.sqlite`  
  SQLite 版本（与 JSON 同构，便于运行时加载与后续迁移）。
- `data/index/wagstaff_catalog_index_v1.json`  
  紧凑索引（用于 WebCraft 列表/搜索与后续 DB 迁移）。
- `data/index/wagstaff_i18n_v1.json`  
  语言层索引（names/desc/quotes 等）。
- `data/index/tag_overrides_v1.json`  
  人工标签修订（可选）。
- `data/index/wagstaff_tuning_trace_v1.json`  
  独立链路索引（可选，便于裁剪）。

SQLite 产物表（派生，摘要）：
- v4 结构以 `db_schema_version=4` 标记，细节见 `docs/specs/SQLITE_V4_SPEC.md`。
- 文件名仍以 catalog JSON 的 schema 版本为准（v2），SQLite 结构版本通过 `db_schema_version` 区分。
- `items`：`id/kind/name/*_json/raw_json`
- `item_stats`：`item_id/stat_key/expr/value_json/trace_key/raw_json`
- `item_*` join 表：category/behavior/source/tag/component/slot
- `assets`：`id/name/icon/image/atlas/build/bank/raw_json`
- `craft_meta` / `craft_recipes` / `craft_ingredients`
- `cooking_recipes` / `cooking_ingredients`
- `catalog_index`：`id/name/icon/kind/*_json`（列表/检索）
- `tuning_trace`：`trace_key/raw_json`（可选）

## 3. 核心实体草案

### 3.0.1 顶层结构（当前实现）

`wagstaff_catalog_v2.json` 顶层结构如下：
- `schema_version`
- `meta`
- `items`
- `assets`
- `craft`
- `cooking`
- `cooking_ingredients`
- `stats`

### 3.0 Meta (统一产物元信息)

建议字段：
- `schema`：产物版本号
- `project_version`：项目版本（统一版本入口）
- `index_version`：索引版本（与 schema 独立）
- `generated`：构建时间 (ISO8601)
- `tool`：构建工具名
- `sources`：构建输入来源（scripts_zip / scripts_dir / resource_index 等）

当前实现额外字段：
- `tuning_mode`
- `scripts_sha256_12`
- `scripts_zip`
- `scripts_dir`

### 3.1 Item（统一实体）

每个 item 对应一个 prefab id，必要时允许 `aliases` 处理别名。

字段建议：
- `id`：prefab id（小写）
- `kind`：`character|creature|structure|item|plant|fx`
- `categories`：多值（见第 4 节）
- `behaviors`：多值（见第 4 节）
- `sources`：多值（craft/cook/loot/spawn/natural/event）
- `slots`：装备槽位（见第 4 节）
- `components`：prefab 组件名列表（用于行为推导）
- `tags`：prefab 标签（用于行为推导）
- `assets`：icon/atlas/image 等引用（可为空）
- `stats`：组件属性/方法推导出的关键数值（weapon_damage/uses/armor 等）
- `prefab_files`：prefab 源文件路径列表（用于溯源）
- `prefab_assets`：prefab Asset 原始声明（原始引用）
- `brains` / `stategraphs` / `helpers`：AI 与辅助函数线索

当前实现说明：
- `recipes` / `aliases` 尚未落盘。
- `stats` 单元结构为：
  - `expr`：原始表达式
  - `value`：解析值（可为空）
  - `expr_resolved`：解析后的表达式（可为空）
  - `trace_key`：可选，指向 trace 索引键
  - `source`：可选，`prefab` / `component_default` / `derived`
  - `source_component`：可选，`source=component_default` 时记录来源组件

### 3.2 Recipe（Craft）

字段建议：
- `id` / `product` / `ingredients`
- `tab` / `filters` / `builder_tags` / `tech`
- `station_tag` / `builder_skill`
- `tuning`（对材料数量/消耗等可选追踪）

当前实现结构：
- `craft.schema`
- `craft.recipes`（每个 recipe 保留 `ingredients` + `amount_value`）
- `craft.aliases`
- `craft.filter_defs` / `craft.filter_order`

### 3.3 Cooking

字段建议：
- `id` / `card_ingredients` / `foodtype` / `tags`
- `priority` / `weight` / `cooktime`
- `hunger` / `health` / `sanity` / `perishtime`
- `tuning`（对上述字段）

当前实现说明：
- Cooking 字段在 `value_only` 下直接落盘数值。
- `tuning_mode=full` 时字段为 `{value, expr, trace}` 结构。

### 3.3.1 Cooking Ingredients

字段建议：
- `id`
- `tags`：料理标签贡献（如 meat/veggie/sweet/monster/egg）
- `tags_expr`：无法解析为数值的表达式（可选）
- `sources`：来源脚本列表（可选）
- `name` / `atlas` / `image` / `prefab` / `foodtype`（可选）

### 3.4 Assets

字段建议：
- `icons`：`{id: "static/icons/{id}.png"}`
- `atlas`/`image`/`build`/`bank` 等原始引用
- `sources`：来源路径（inventoryimages.xml / prefab Asset / data/*）

当前实现说明：
- `assets` 为 `{id: {icon, atlas?, image?}}` 的轻量映射。

### 3.5 I18n Index

字段建议：
- `names`：`{lang: {id: localized_name}}`
- `ui`：`{lang: {key: text}}`（WebCraft UI 词条）
- `meta`：构建来源（po 路径 / scripts.zip / ui.json）

### 3.6 Stats 解析覆盖面（当前实现）

- 组件方法解析：`weapon` / `combat` / `finiteuses` / `armor` / `edible` / `perishable` / `fueled` / `equippable` / `insulator` / `waterproofer` / `light` / `stackable` / `health` / `sanity` / `sanityaura` / `hunger` / `locomotor` / `rechargeable` / `heater` / `planardamage` / `planararmor` / `workable`
- 组件属性解析：覆盖 `equippable` / `edible` / `insulator` / `waterproofer` / `stackable` / `health` / `sanity` / `hunger` / `locomotor` / `planardamage` / `planararmor` / `workable` 等

## 4. 标签体系（建议）

### 4.1 kind（主类）
`character | creature | structure | item | plant | fx`

### 4.2 category（功能类别）
`weapon | armor | tool | food | resource | magic | container | light | deployable | trap | boat | farm | decor | toy`

### 4.3 behavior（组件行为）
`equippable | edible | stackable | burnable | perishable | repairable | fuel | tradable | hauntable | deployable`

### 4.4 source（来源）
`craft | cook | loot | spawn | natural | event`

### 4.5 slot（可选）
`head | body | hand | back`

## 5. TUNING trace 模式

字段可同时输出：
- `value`：数值（可直接展示）
- `expr`：原始表达式
- `trace`：链路结构（refs/steps/chain）

输出模式：
- `value_only`：只输出 value
- `full`：输出 value + trace

建议将 trace 拆分到 `wagstaff_tuning_trace_v1.json`，在需要时按 id 拉取。

当前实现说明：
- Trace 索引是 `{trace_key: trace}` 的映射。
- `trace_key` 形式：
  - `item:{id}:stat:{stat_key}`
  - `craft:{recipe}:ingredient:{item}`
  - `cooking:{recipe}:{field}`

## 6. tag overrides（人工修订）

建议结构示例见：`conf/samples/tag_overrides.example.json`

逻辑建议：
- `add`：追加标签
- `remove`：移除标签
- `set`：强制覆盖（必要时）

## 7. 迁移建议（上层改造）

- WebCraft `catalog` 页面读取 `wagstaff_catalog_v2.json` 的 `items`
- WebCraft 搜索改为 “items + recipes + cooking” 多源索引
- i18n 层独立加载（不依赖 catalog）
- icon 服务改为读取 `assets.icon` / icon index 统一入口
- CLI/wiki 使用 v2 结构，避免 direct prefab 解析
- 旧 v1 产物可删除（或仅保留构建回滚）

## 8. Catalog Index v1 规范（wagstaff_catalog_index_v1.json）

用途：提供 WebCraft 列表/搜索的紧凑索引，减少 UI 初始化负担。

### 8.1 顶层结构

```json
{
  "schema_version": 1,
  "meta": { ... },
  "counts": { "items_total": 0, "items_with_icon": 0, "icon_only": 0 },
  "items": [ ... ],
  "indexes": { ... }
}
```

### 8.2 meta（当前实现）

- `schema` / `generated` / `tool`
- `sources.catalog`: `wagstaff_catalog_v2.json`
- `sources.scripts_zip` / `sources.scripts_dir`
- `catalog_schema`: catalog v2 schema 版本
- `scripts_sha256_12` / `scripts_zip` / `scripts_dir`

### 8.3 items（紧凑条目）

每个条目结构：

```json
{
  "id": "spear",
  "name": "Spear",
  "image": "static/icons/spear.png",
  "icon": "static/icons/spear.png",
  "has_icon": true,
  "icon_only": false,
  "kind": "item",
  "categories": ["weapon"],
  "behaviors": ["equippable"],
  "sources": ["craft"],
  "tags": ["pointy", "sharp", "weapon"],
  "components": ["equippable", "finiteuses", "inventoryitem", "weapon"],
  "slots": []
}
```

约束：
- `items` 全量按 `id` 排序。
- `icon_only=true` 表示仅来自 icon index/asset 映射、但 catalog v2 无实体。
- `image` 通常为 icon，也可能是 atlas/image（当 icon 缺失时）。

### 8.4 indexes（倒排索引）

结构统一为 `{label: [id...]}`，id 列表去重 + 排序：

```json
{
  "by_kind": { "item": ["spear", ...] },
  "by_category": { "weapon": ["spear", ...] },
  "by_behavior": { "equippable": ["spear", ...] },
  "by_source": { "craft": ["spear", ...] },
  "by_component": { "weapon": ["spear", ...] },
  "by_tag": { "sharp": ["spear", ...] },
  "by_slot": { "hand": ["spear", ...] }
}
```

## 9. WebCraft API 契约（关键接口）

### 9.1 GET `/api/v1/catalog/index`

返回 Catalog 索引的紧凑列表（前端列表/搜索使用）：

参数：
- `offset`：可选，默认 0（分页起点）
- `limit`：可选，默认 200（1~2000）

```json
{
  "items": [ ... ],
  "count": 0,
  "total": 0,
  "offset": 0,
  "limit": 200,
  "icon": {
    "mode": "off|static|dynamic|auto",
    "static_base": "/static/data/icons",
    "api_base": "/api/v1/icon"
  }
}
```

说明：
- `items` 的结构等同于 `wagstaff_catalog_index_v1.json.items`。
- 若索引文件缺失，后端会用 catalog v2 + icon index 动态拼装同结构返回。
- `icon` 表示前端图片加载策略（静态优先/动态回退）。
- 支持 `Cache-Control`/`ETag` 以便前端缓存（auto-reload 模式下关闭）。

### 9.2 GET `/api/v1/catalog/search`

返回 Catalog 索引的搜索结果（后端过滤 + 评分排序）：

参数：
- `q`：必填，支持 `kind:xxx`/`cat:xxx`/`src:xxx`/`tag:xxx`/`comp:xxx`/`slot:xxx` 过滤
- `offset`：可选，默认 0（分页起点）
- `limit`：可选，默认 200（1~2000）

```json
{
  "q": "kind:weapon spear",
  "items": [ ... ],
  "count": 0,
  "total": 0,
  "offset": 0,
  "limit": 200
}
```

说明：
- `items` 的结构等同于 `wagstaff_catalog_index_v1.json.items`。
- 支持 `Cache-Control`/`ETag` 以便前端缓存（auto-reload 模式下关闭）。

### 9.3 GET `/api/v1/tuning/trace`

用于按 key 或 prefix 拉取 trace 结构（来源 `wagstaff_tuning_trace_v1.json`）。

参数：
- `key`：完整 key，返回单条 trace
- `prefix`：前缀过滤，返回多条
- `limit`：可选，默认 2000（1~10000）

响应：

```json
// key 模式
{ "enabled": true, "key": "item:spear:stat:weapon_damage", "trace": { ... } }

// prefix 模式
{ "enabled": true, "prefix": "cooking:butterflymuffin", "traces": { "...": { ... } }, "count": 1 }
```

trace 结构（当前实现）：
- `expr`：原始表达式
- `value`：解析值
- `expr_resolved`：解析后的表达式
- `refs`：引用展开（含 steps/chain）
- `expr_chain`：链路串联

若 trace 索引未加载：`{"enabled": false, "trace": null, "traces": {}, "count": 0}`。
