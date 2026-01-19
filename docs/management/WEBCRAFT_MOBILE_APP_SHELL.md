# WebCraft Mobile App Shell 规划

目标：先落地 Cooking（模拟/探索）移动端 App 风格体验，同时为 Craft/Catalog 全站统一 App Shell 做基础。

## 约束

- 遵循 `docs/guides/DEV_GUIDE.md`，不引入新构建链、不改变 API 形态。
- 仅使用模板 + CSS/JS，移动端样式通过 `data-app-shell="1"` opt-in。
- 桌面端布局不回退、不稀释现有信息密度。

## 设计方向（移动端）

- 单列主流程：锅位/操作 → 食材选择 → 结果 → 详情。
- App Shell：底部固定导航，顶部轻量标题栏。
- 触控优先：Chip/按钮 ≥ 44px，横向滚动过滤器，安全区（safe-area）适配。

## 架构方案

### 1) App Shell 基础（可复用）

- 约定：`body[data-app-shell="1"]` 启用移动端 App Shell。
- 通用样式：
  - `apps/webcraft/static/css/base.css` 提供 `.app-nav` 组件样式与移动端激活规则。
  - `layout` 增加 bottom padding，避开底部导航覆盖。
- 通用结构：
  - 模板新增 `<nav class="app-nav">`，包含 `appNavCraft/appNavCooking/appNavCatalog`。
  - 页面 JS 负责设置 href 与 active 状态。

### 2) Cooking 工具页落地

- `data-role="tool"` 页面移动端重排为：
  - `#toolBox`（粘性锅位条 + 操作）
  - `#ingredientPicker`（主交互区）
  - `#resultBox`（结果卡片/列表）
  - `#detail`（详情/规则）
- 结果触发后自动聚焦到结果区（移动端）。
- 结果区在移动端以底部抽屉呈现，可折叠/展开以保证食材选择区可用。

### 3) 扩展到全站（后续）

- Craft/Catalog 页面：
  - 添加 `data-app-shell="1"` 与底部 `app-nav`。
  - 在各自 JS 中设置 `appNav*` 的 href 与 active。
- 可选：抽取 App Shell 片段到模板片段（若后续引入更轻量的模板拼装）。

## 分阶段执行

- Phase A（本次）：
  - 仅落地 Cooking 的 App Shell 与移动端交互重排。
  - 建立 `app-nav` 组件与 `data-app-shell` 约定。
- Phase B（后续）：
  - Craft/Catalog 迁移至 App Shell。
  - 增加统一的移动端导航规则与交互规范。

## 验证清单

- Cooking 模拟/探索在移动端可完整使用，无需滚动到顶部操作。
- 底部导航可切换三大入口。
- 桌面端布局不受影响。

## 记录

- App Shell 规范写入 `DEV_GUIDE.md`。
- 变更写入 `PROJECT_STATUS.json`。
