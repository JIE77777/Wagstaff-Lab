# Cooking 探索/模拟升级方案（归档）

目的：将 Cooking 页面升级为“百科（主）/探索/模拟”三入口体验，并提供可解释的结果与排序公式。

## 1. 机制理解（DST Cookpot）

- 料理由 `test(ingredients, tags)` 决定，`ingredients` 为槽位物品，`tags` 为食材属性汇总（meat/veggie/fruit/sweet/monster/egg/dairy 等）。
- 约束分两类：
  - 特定食材：需要/排除指定物品（names.X）。
  - 属性约束：对 tags 数值进行比较（tags.X >= 1.5 等）。
- 匹配后的选择规则：优先按 priority，高优先级内按 weight 抽取；无匹配时为 wetgoop。

## 2. 目标体验

- 入口清晰：百科 / 探索 / 模拟三种模式。
- 结果可解释：显示排序公式、结果依据与缺失项（接近可做）。
- 视觉结构：卡片为主，可切换高密度列表。
- 探索/模拟耦合：首个槽位填入即触发探索提示。

## 3. 数据契约与解析

- 新增 `cooking_ingredients` 索引：
  - `id`
  - `tags`（数值化）
  - `tags_expr`（无法解析的表达式）
  - `sources`（来源脚本）
- 来源：`scripts/ingredients.lua` / `scripts/cooking.lua`。

## 4. 结果与排序说明

排序公式（默认）：

```
score = priority * 1000 + weight * 100 - missing_penalty
missing_penalty = Σ(缺失 tag 值 * 10) + Σ(缺失食材数 * 50)
```

可解释字段：
- priority / weight
- tags / names 约束的满足情况
- 接近可做：缺失标签/缺失食材与差距值

## 5. API 设计（WebCraft）

- `/api/v1/cooking/explore`
  - 输入：`slots`（允许少于 4）
  - 输出：`cookable` 与 `near_miss`，含排序分数与缺失解释
- `/api/v1/cooking/simulate`
  - 输入：`slots`（必须 4）
  - 输出：`result`、`candidates`、公式说明与缺失解释

## 6. UI 约束

- 探索/模拟页必须显示：
  - 排序公式说明
  - 结果卡片（可做/接近可做）
  - 结果详情中的约束解释
- 移动端避免信息被固定头部遮挡。
