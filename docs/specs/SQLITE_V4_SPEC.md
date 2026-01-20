# Wagstaff SQLite v4 结构设计

目标：提供统一、可扩展的 SQLite 存储结构，支持 catalog / mechanism / i18n 等索引的一致落盘与查询。

## 1. 版本策略

- **db_schema_version**：SQLite 结构版本，当前为 `4`。
- **schema_version**：JSON 索引的 schema 版本（如 catalog v2 / mechanism v1）。
- **project_version / index_version**：来自 `conf/version.json`。

## 2. 文件布局（建议）

当前落盘仍保持按索引拆分：

- `data/index/wagstaff_catalog_v2.sqlite`：catalog v2（items/craft/cooking/assets 等）
- `data/index/wagstaff_mechanism_index_v1.sqlite`：mechanism v1（components/prefab links 等）

SQLite v4 结构以 **表分组** 方式定义；单个文件可只实现其所需的表分组。

## 3. 通用约定

- `id` 默认指 prefab id（小写）。
- `*_json` 字段为 JSON 文本（保持原始结构，便于回溯）。
- 所有 JSON/SQLite 产物在 `meta` 中写入 `project_version/index_version`。
- 规范的 join 表用于快速过滤；原始结构保留在 `raw_json`。

## 4. 通用表（所有 DB 必备）

```sql
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

meta 建议写入的 key：
- `schema_version`（JSON schema 版本）
- `db_schema_version`（SQLite 结构版本）
- `meta`（完整 meta JSON）
- `stats`（统计信息 JSON，可选）

## 5. Catalog 表分组

### 5.1 Items

```sql
CREATE TABLE items (
  id TEXT PRIMARY KEY,
  kind TEXT,
  name TEXT,
  categories_json TEXT,
  behaviors_json TEXT,
  sources_json TEXT,
  tags_json TEXT,
  components_json TEXT,
  slots_json TEXT,
  assets_json TEXT,
  prefab_files_json TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE item_stats (
  item_id TEXT NOT NULL,
  stat_key TEXT NOT NULL,
  expr TEXT,
  expr_resolved TEXT,
  trace_key TEXT,
  value_json TEXT,
  raw_json TEXT,
  PRIMARY KEY (item_id, stat_key)
);
```

Join 表（过滤/检索）：

```sql
CREATE TABLE item_categories (item_id TEXT NOT NULL, category TEXT NOT NULL, PRIMARY KEY (item_id, category));
CREATE TABLE item_behaviors (item_id TEXT NOT NULL, behavior TEXT NOT NULL, PRIMARY KEY (item_id, behavior));
CREATE TABLE item_sources (item_id TEXT NOT NULL, source TEXT NOT NULL, PRIMARY KEY (item_id, source));
CREATE TABLE item_tags (item_id TEXT NOT NULL, tag TEXT NOT NULL, PRIMARY KEY (item_id, tag));
CREATE TABLE item_components (item_id TEXT NOT NULL, component TEXT NOT NULL, PRIMARY KEY (item_id, component));
CREATE TABLE item_slots (item_id TEXT NOT NULL, slot TEXT NOT NULL, PRIMARY KEY (item_id, slot));
```

### 5.2 Assets

```sql
CREATE TABLE assets (
  id TEXT PRIMARY KEY,
  name TEXT,
  icon TEXT,
  image TEXT,
  atlas TEXT,
  build TEXT,
  bank TEXT,
  raw_json TEXT NOT NULL
);
```

### 5.3 Craft / Cooking

```sql
CREATE TABLE craft_meta (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);

CREATE TABLE craft_recipes (
  name TEXT PRIMARY KEY,
  product TEXT,
  tab TEXT,
  tech TEXT,
  builder_skill TEXT,
  station_tag TEXT,
  filters_json TEXT,
  builder_tags_json TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE craft_ingredients (
  recipe_name TEXT NOT NULL,
  item_id TEXT NOT NULL,
  amount_num REAL,
  amount_value REAL,
  raw_json TEXT,
  PRIMARY KEY (recipe_name, item_id)
);

CREATE TABLE cooking_recipes (
  name TEXT PRIMARY KEY,
  priority REAL,
  weight REAL,
  foodtype TEXT,
  hunger_json TEXT,
  health_json TEXT,
  sanity_json TEXT,
  perishtime_json TEXT,
  cooktime_json TEXT,
  tags_json TEXT,
  card_ingredients_json TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE cooking_ingredients (
  item_id TEXT PRIMARY KEY,
  tags_json TEXT,
  tags_expr TEXT,
  sources_json TEXT,
  raw_json TEXT NOT NULL
);
```

### 5.4 Catalog Index（列表/检索）

```sql
CREATE TABLE catalog_index (
  id TEXT PRIMARY KEY,
  name TEXT,
  icon TEXT,
  image TEXT,
  has_icon INTEGER,
  icon_only INTEGER,
  kind TEXT,
  categories_json TEXT,
  behaviors_json TEXT,
  sources_json TEXT,
  tags_json TEXT,
  components_json TEXT,
  slots_json TEXT
);
```

可选 FTS：

```sql
CREATE VIRTUAL TABLE catalog_index_fts
USING fts5(id, name, content='catalog_index', content_rowid='rowid');
```

### 5.5 Tuning Trace（可选）

```sql
CREATE TABLE tuning_trace (
  trace_key TEXT PRIMARY KEY,
  raw_json TEXT NOT NULL
);
```

### 5.6 关键索引（建议）

```sql
CREATE INDEX idx_items_kind ON items(kind);
CREATE INDEX idx_item_stats_key ON item_stats(stat_key);
CREATE INDEX idx_item_stats_item ON item_stats(item_id);
CREATE INDEX idx_item_cat ON item_categories(category);
CREATE INDEX idx_item_beh ON item_behaviors(behavior);
CREATE INDEX idx_item_src ON item_sources(source);
CREATE INDEX idx_item_tag ON item_tags(tag);
CREATE INDEX idx_item_comp ON item_components(component);
CREATE INDEX idx_item_slot ON item_slots(slot);
CREATE INDEX idx_craft_product ON craft_recipes(product);
CREATE INDEX idx_craft_tab ON craft_recipes(tab);
CREATE INDEX idx_craft_ing_item ON craft_ingredients(item_id);
CREATE INDEX idx_cooking_foodtype ON cooking_recipes(foodtype);
CREATE INDEX idx_catalog_name ON catalog_index(name);
```

## 6. Mechanism 表分组

```sql
CREATE TABLE components (
  id TEXT PRIMARY KEY,
  class_name TEXT,
  path TEXT,
  aliases_json TEXT,
  methods_json TEXT,
  fields_json TEXT,
  events_json TEXT,
  requires_json TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE component_fields (
  component_id TEXT,
  field TEXT,
  PRIMARY KEY (component_id, field)
);
CREATE TABLE component_methods (
  component_id TEXT,
  method TEXT,
  PRIMARY KEY (component_id, method)
);
CREATE TABLE component_events (
  component_id TEXT,
  event TEXT,
  PRIMARY KEY (component_id, event)
);

CREATE TABLE prefabs (
  id TEXT PRIMARY KEY,
  components_json TEXT,
  tags_json TEXT,
  brains_json TEXT,
  stategraphs_json TEXT,
  helpers_json TEXT,
  files_json TEXT,
  events_json TEXT,
  assets_json TEXT,
  component_calls_json TEXT,
  raw_json TEXT NOT NULL
);

CREATE TABLE prefab_components (
  prefab_id TEXT,
  component_id TEXT,
  PRIMARY KEY (prefab_id, component_id)
);

CREATE TABLE links (
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  target TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relation TEXT
);
```

说明：`relation` 为可选字段，缺省时视为 `prefab_component`。

状态机 / 脑图扩展表（v4 预留）：

```sql
CREATE TABLE stategraphs (id TEXT PRIMARY KEY, raw_json TEXT);
CREATE TABLE stategraph_states (stategraph_id TEXT, state_name TEXT, raw_json TEXT);
CREATE TABLE stategraph_events (stategraph_id TEXT, event TEXT, raw_json TEXT);
CREATE TABLE stategraph_edges (stategraph_id TEXT, src TEXT, dst TEXT, event TEXT);

CREATE TABLE brains (id TEXT PRIMARY KEY, raw_json TEXT);
CREATE TABLE brain_nodes (brain_id TEXT, node_id TEXT, raw_json TEXT);
CREATE TABLE brain_edges (brain_id TEXT, src TEXT, dst TEXT, raw_json TEXT);
```

关键索引（建议）：

```sql
CREATE INDEX idx_comp_method ON component_methods(method);
CREATE INDEX idx_comp_field ON component_fields(field);
CREATE INDEX idx_prefab_comp ON prefab_components(component_id);
CREATE INDEX idx_links_source ON links(source, source_id);
CREATE INDEX idx_links_target ON links(target, target_id);
```

## 7. I18n 表分组（可选）

```sql
CREATE TABLE i18n_names (
  lang TEXT NOT NULL,
  id TEXT NOT NULL,
  name TEXT NOT NULL,
  PRIMARY KEY (lang, id)
);

CREATE TABLE i18n_ui (
  lang TEXT NOT NULL,
  key TEXT NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY (lang, key)
);

CREATE TABLE i18n_tags (
  lang TEXT NOT NULL,
  tag TEXT NOT NULL,
  label TEXT NOT NULL,
  source TEXT,
  PRIMARY KEY (lang, tag)
);
```

## 8. 迁移策略（建议）

1. 先统一写入 `db_schema_version=4`（已完成）。
2. 新增 v4 DDL builder，优先替换 catalog SQLite 产物。
3. WebCraft 加载逻辑优先 v4 schema，若缺失再回退旧表结构。
4. 完成后同步 mechanism SQLite，补齐 links/fts 索引与一致性校验。
