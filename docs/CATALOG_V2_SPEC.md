# Wagstaff Catalog v2 规范草案

目标：对 DST 做“全面理解与展示”，形成稳定可迁移的索引产物。

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
- `data/index/wagstaff_i18n_v1.json`  
  语言层索引（names/desc/quotes 等）。
- `data/index/tag_overrides_v1.json`  
  人工标签修订（可选）。
- `data/index/wagstaff_tuning_trace_v1.json`  
  独立链路索引（可选，便于裁剪）。

## 3. 核心实体草案

### 3.1 Item（统一实体）

每个 item 对应一个 prefab id，必要时允许 `aliases` 处理别名。

字段建议：
- `id`：prefab id（小写）
- `kind`：`character|creature|structure|item|plant|fx`
- `categories`：多值（见第 4 节）
- `behaviors`：多值（见第 4 节）
- `sources`：多值（craft/cook/loot/spawn/natural/event）
- `components`：prefab 组件名列表（用于行为推导）
- `tags`：prefab 标签（用于行为推导）
- `assets`：icon/atlas/image 等引用
- `stats`：组件属性/方法推导出的关键数值（weapon_damage/uses/armor 等）
- `prefab_files`：prefab 源文件路径列表（用于溯源）
- `prefab_assets`：prefab Asset 原始声明（原始引用）
- `brains` / `stategraphs` / `helpers`：AI 与辅助函数线索
- `recipes`：关联配方列表（craft/cooking）
- `tuning`：字段级 TUNING 引用（可裁剪 trace）

### 3.2 Recipe（Craft）

字段建议：
- `id` / `product` / `ingredients`
- `tab` / `filters` / `builder_tags` / `tech`
- `station_tag` / `builder_skill`
- `tuning`（对材料数量/消耗等可选追踪）

### 3.3 Cooking

字段建议：
- `id` / `card_ingredients` / `foodtype` / `tags`
- `priority` / `weight` / `cooktime`
- `hunger` / `health` / `sanity` / `perishtime`
- `tuning`（对上述字段）

### 3.4 Assets

字段建议：
- `icons`：`{id: "static/icons/{id}.png"}`
- `atlas`/`image`/`build`/`bank` 等原始引用
- `sources`：来源路径（inventoryimages.xml / prefab Asset / data/*）

### 3.5 I18n Index

字段建议：
- `names`：`{lang: {id: localized_name}}`
- `ui`：`{lang: {key: text}}`（WebCraft UI 词条）
- `meta`：构建来源（po 路径 / scripts.zip / ui.json）

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

## 6. tag overrides（人工修订）

建议结构示例见：`conf/samples/tag_overrides.example.json`

逻辑建议：
- `add`：追加标签
- `remove`：移除标签
- `set`：强制覆盖（必要时）

## 7. 迁移清单（上层改造）

- [ ] WebCraft `catalog` 页面读取 `wagstaff_catalog_v2.json` 的 `items`
- [ ] WebCraft 搜索改为 “items + recipes + cooking” 多源索引
- [ ] i18n 层独立加载（不依赖 catalog）
- [ ] icon 服务改为读取 `assets.icons` 统一入口
- [ ] CLI/wiki 使用 v2 结构，避免 direct prefab 解析
- [ ] 旧 v1 产物可删除（或仅保留构建回滚）
