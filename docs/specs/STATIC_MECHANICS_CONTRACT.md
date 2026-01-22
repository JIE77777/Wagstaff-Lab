# Static Mechanics Data Contract (Draft)

Version: v4.0.0-dev  
Status: Draft (proposal)

本契约用于定义“静态机制解析”产物的最小数据形态与落盘范围，强调可解释、可检索与可复用。

## 1. Scope

静态机制解析覆盖以下数据域：

- Prefab/Item 基础信息
- Component 绑定关系
- Component 字段数值（stats）
- Craft/Cooking/Farming 规则
- Tuning trace（数值来源链路）
- i18n 文本与 icon 资产

## 2. Outputs (data/index)

必须落盘在 `data/index/`，并在 `wagstaff_index_manifest.json` 记录。

- `wagstaff_catalog_v2.json`
- `wagstaff_catalog_v2.sqlite`
- `wagstaff_catalog_index_v1.json`
- `wagstaff_mechanism_index_v1.json`
- `wagstaff_mechanism_index_v1.sqlite`
- `wagstaff_tuning_trace_v1.json`
- `wagstaff_farming_defs_v1.json`
- `wagstaff_i18n_v1.json`
- `wagstaff_icon_index_v1.json`
- `wagstaff_resource_index_v1.json`
- `wagstaff_index_manifest.json`

## 3. Common Meta (JSON indexes)

除 `wagstaff_tuning_trace_v1.json` 外，其余 JSON 索引统一包含：

```yaml
schema_version: <int>
meta:
  schema: <string>
  generated: <iso-8601>
  tool: <string>
  project_version: <string>
  index_version: <string>
  sources: <array>
  scripts_sha256_12: <string>
  scripts_zip: <string|null>
  scripts_dir: <string|null>
```

## 4. Catalog v2 (JSON)

`wagstaff_catalog_v2.json` 必须包含：

```yaml
schema_version: 2
meta: { ... }
items: { <prefab_id>: <item_doc> }
assets: { ... }
craft: { ... }
cooking: { ... }
cooking_ingredients: { ... }
stats: { <prefab_id>: <stats_doc> }
```

详细字段见 `docs/specs/CATALOG_V2_SPEC.md`。
补充：`stats` 可携带 `source/source_component` 标记默认值或推导值来源（组件默认值或 derived 推导）。

## 5. Catalog Index (JSON)

`wagstaff_catalog_index_v1.json` 必须包含：

```yaml
schema_version: 1
meta: { ... }
counts: { items_total: <int>, items_with_icon: <int>, icon_only: <int> }
items: [<prefab_id>, ...]
indexes: { <index_name>: <index_payload> }
```

## 6. Mechanism Index (JSON)

`wagstaff_mechanism_index_v1.json` 必须包含：

```yaml
schema_version: 1
meta: { ... }
counts: { components_total: <int>, prefabs_total: <int>, ... }
components: { <component_id>: <component_doc> }
prefabs: { <prefab_id>: <prefab_doc> }
component_usage: { <component_id>: <counts> }
links: [<edge>, ...]
```

详细字段见 `docs/specs/MECHANISM_INDEX_SPEC.md`。

## 7. Tuning Trace (JSON)

`wagstaff_tuning_trace_v1.json` 为 key-value map：

```yaml
"item:<prefab_id>:stat:<key>":
  expr: <string>
  value: <number|null>
  expr_resolved: <string|null>
  refs: <object>
  expr_chain: <string|null>
```

注：该文件不包含统一 `meta`，由 index manifest 记录版本与来源。

## 8. SQLite v4

SQLite 结构以 `docs/specs/SQLITE_V4_SPEC.md` 为准，必须包含：

- `db_schema_version=4`
- catalog/mechanism 对应表集与索引
- catalog FTS 与 tuning_trace 表

## 9. Quality & Coverage (derived)

质量指标由 `data/reports/quality_gate_report.json` 与 `catalog_quality_report.json` 产出。
静态机制覆盖基准由 `data/reports/static_mechanics_coverage_report.json` 输出。
覆盖建议按 C0/C1/C2 三层衡量（组件/字段/数值）。

## 10. Non-goals

- 行为/AI/stategraph/brain 解析不在此契约范围。
