# WebCraft UI 模块化改造计划

目标：在不更换技术栈的前提下，拆分 WebCraft UI 结构，降低 `apps/webcraft/ui.py` 体积与耦合，减少跨页 JS 依赖导致的回归，同时保持 API/数据结构稳定。

## 约束与原则

- 遵循 `docs/guides/DEV_GUIDE.md`（UI 静态资源必须落盘 `apps/webcraft/static/`，对外挂载 `/static/app`）。
- 不引入构建链，不改变 API 与数据产物结构。
- 迁移过程按“低风险 → 高改动”渐进执行。
- 每阶段结束都需手动验证 `/catalog` `/craft` `/cooking` 运行无 JS 错误。

## 范围

- 拆分 CSS/JS/模板结构，建立 core + pages 分层。
- `ui.py` 变薄，仅负责模板注入与资源引用。

非目标：
- 不引入 React/Vue/Vite 等构建体系。
- 不改动后端 API 形态与路径。

## 分阶段计划

### Phase 0：脚手架与入口对齐（低风险）

- 创建目录：
  - `apps/webcraft/static/css/`
  - `apps/webcraft/static/js/core/`
  - `apps/webcraft/static/js/pages/`
- 添加空占位资源：
  - `static/css/base.css`
  - `static/js/app.js`
- 在模板中引入 `/static/app/css/base.css` 与 `/static/app/js/app.js`（先不移除内联 CSS/JS）。

输出：
- 资源路径与加载链路建立。

### Phase 1：CSS 拆分

- 把 `_SHARED_CSS` 拆为：
  - `base.css`（跨页面通用）
  - `catalog.css` / `craft.css` / `cooking.css`（页面样式）
- `ui.py` 内联 CSS 逐步移除，仅保留极少量页面必要样式（如无则清空）。

输出：
- UI 样式可分文件维护，避免大段内联。

### Phase 2：JS 拆分（核心）

- 抽取通用工具到 `static/js/core/`（api/dom/i18n/icons/shared）。
- 页面逻辑拆入 `static/js/pages/`（catalog/craft/cooking）。
- `static/js/app.js` 通过 `body` class 或 `data-page` 初始化对应页面。
- 禁止页面之间互相引用函数。

输出：
- 跨页函数缺失问题根治。

### Phase 3：模板化 HTML（可选但推荐）

- 新增 `apps/webcraft/templates/*.html`。
- `ui.py` 读取模板并注入 `APP_ROOT` 等变量。

输出：
- HTML 结构可单独编辑，diff 变小。

## 验证清单

- `/` `/catalog` `/craft` `/cooking` 均可正常访问。
- console 无 `ReferenceError` / `Uncaught` 报错。
- i18n（label mode / tags）仍可正常切换与显示。
- 仍支持 `root_path` 部署路径。

## 风险与回滚

- 风险：资源路径写错导致页面空白；JS 拆分造成函数缺失。
- 回滚：保留 Phase 0 的路径引入不影响现状；出现问题可先恢复内联版本。

## 记录

- 每阶段完成需更新：
  - `PROJECT_STATUS.json`（RECENT_LOGS）
  - `docs/guides/DEV_GUIDE.md`（如新增结构约束）

## 状态

- 2026-01-17：Phase 1-3 完成，CSS/JS/模板迁移落地，`ui.py` 保留模板渲染。
