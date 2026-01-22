# Behavior Graph Spec (Draft)

Version: v4.0.0-dev  
Status: Draft (proposal)

本规范用于定义“行为图谱解析”产物的数据契约，覆盖 stategraph 与 brain 的结构化输出。

## 1. Scope

- StateGraph：状态机结构、状态、转移、触发与条件
- Brain/BehaviorTree：节点、边、条件与优先级
- Prefab 关联：prefab 与图谱的映射关系（来源资源索引与脚本解析）

## 2. Outputs (data/index)

建议落盘：

- `data/index/wagstaff_behavior_graph_v1.json`
- （可选）`data/reports/behavior_graph_summary.md`

## 3. Common Meta

```yaml
schema_version: 1
meta:
  schema: behavior_graph_v1
  generated: <iso-8601>
  tool: <string>
  project_version: <string>
  index_version: <string>
  sources: <array>
  scripts_sha256_12: <string>
  scripts_zip: <string|null>
  scripts_dir: <string|null>
```

## 4. Top-level Structure (JSON)

```yaml
schema_version: 1
meta: { ... }
counts:
  stategraphs_total: <int>
  brains_total: <int>
  prefabs_total: <int>
stategraphs: { <graph_id>: <stategraph_doc> }
brains: { <graph_id>: <brain_doc> }
prefab_links:
  <prefab_id>:
    stategraph: <graph_id|null>
    brain: <graph_id|null>
```

## 5. StateGraph Doc

```yaml
id: <string>
source: <path>
states: [<state_id>, ...]
edges:
  - from: <state_id>
    to: <state_id>
    trigger: <string|null>
    condition: <string|null>
    tags: [<string>, ...]
timers: [<timer_id>, ...]
events: [<event_id>, ...]
notes: <string|null>

说明：
- `trigger` 常见为 `event`/`goto`（当前为启发式，后续可细化为 onenter/onexit 等）
- `timers` 当前格式为 `<state>:<expr>`（TimeEvent 触发表达式）
```

## 6. Brain Doc

```yaml
id: <string>
source: <path>
nodes:
  - id: <string>
    kind: <string>
    condition: <string|null>
    params: <object|null>
edges:
  - from: <node_id>
    to: <node_id>
    rule: <string|null>
priority: <string|null>
notes: <string|null>

说明：
- `params` 目前包含 `args_total` 与 `args_preview`（前 4 个参数的摘要）
```

## 7. Confidence & Trace

所有节点/边允许附带：

```yaml
trace:
  expr: <string>
  source: <path>
  confidence: exact|derived|conditional
```

## 8. Non-goals

- 行为结果数值化（例如 DPS/命中率）不在本阶段范围。
- 不保证完整还原运行时逻辑，仅提供可视化与检索所需结构。
