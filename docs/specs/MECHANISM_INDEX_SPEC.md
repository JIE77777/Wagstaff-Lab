# Wagstaff Mechanism Index v1 规范草案

目标：提供 DST 机制解析的最小可查询索引，优先落盘组件定义与 prefab 组件链路。

## 1. 产物与版本

- JSON: `data/index/wagstaff_mechanism_index_v1.json`
- SQLite: `data/index/wagstaff_mechanism_index_v1.sqlite`
- schema_version: 1
- JSON schema: `docs/specs/mechanism_index_v1.schema.json`
- SQLite 结构版本通过 meta 的 `db_schema_version` 标记（当前 v4）。

## 2. 顶层结构（JSON）

```yaml
schema_version: 1
meta: {schema, project_version, index_version, generated, tool, sources, scripts_sha256_12, ...}
counts:
  components_total: int
  prefabs_total: int
  components_used: int
  prefab_component_edges: int
components:
  total_files: int
  items: {component_id: Component}
prefabs:
  items: {prefab_id: PrefabLink}
component_usage:
  component_id: [prefab_id, ...]
links:
  prefab_component: [Link, ...]
```

### 2.1 Component

```yaml
type: "component"
id: "combat"
class_name: "Combat"
aliases: ["Combat", ...]
methods: ["SetDefaultDamage", ...]
fields: ["defaultdamage", ...]
events: ["attacked", ...]
requires: ["components/health", ...]
path: "scripts/components/combat.lua"
```

### 2.2 PrefabLink

```yaml
components: ["combat", "health", ...]
tags: ["monster", ...]
brains: ["brains/spiderbrain", ...]
stategraphs: ["SGspider", ...]
helpers: ["MakeSmallBurnable", ...]
files: ["scripts/prefabs/spider.lua", ...]
events: ["attacked", ...]
assets: [{type: "ANIM", path: "anim/spider.zip"}, ...]
component_calls:
  - component: "combat"
    methods: ["SetDefaultDamage(34)", ...]
    properties: ["defaultdamage = 34", ...]
```

### 2.3 Link

```yaml
source: "prefab"
source_id: "spider"
target: "component"
target_id: "combat"
```

## 3. SQLite 结构

核心表：

- `meta`：包含 `schema_version` 与 `db_schema_version`（SQLite 结构版本，当前 v4）
- `components(id, class_name, path, aliases_json, methods_json, fields_json, events_json, requires_json, raw_json)`
- `component_fields(component_id, field)`
- `component_methods(component_id, method)`
- `component_events(component_id, event)`
- `prefabs(id, components_json, tags_json, brains_json, stategraphs_json, helpers_json, files_json, events_json, assets_json, component_calls_json, raw_json)`
- `prefab_components(prefab_id, component_id)`
- `links(source, source_id, target, target_id, relation)`（relation 可选，缺省视为 prefab_component）

保留扩展表（后续解析落盘）：

- `stategraphs` / `stategraph_states` / `stategraph_events` / `stategraph_edges`
- `brains` / `brain_nodes` / `brain_edges`
- `worldgen_presets` / `worldgen_tasksets` / `worldgen_tasks` / `worldgen_rooms` / `worldgen_layouts` / `worldgen_links`

## 4. 一致性与校验

- `links` 与 `prefab_components` 应可互相推导。
- `prefab_components.component_id` 必须存在于 `components.id`，否则记录为缺失组件。
- `component_usage` 与 `links` 数量应匹配，计入 `counts.prefab_component_edges`。

## 5. 兼容与演进

- v2 可加入 stategraph/brain 解析结果并填充扩展表。
- JSON/SQLite 输出需同步更新 schema_version 与 build_meta。
