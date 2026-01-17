# Wagstaff-Lab 版本演进方向 (v3+)

本文件仅保留**长期方向**，执行计划与进度请统一查看：
- `docs/management/PROJECT_MANAGEMENT.md`

## 1. 架构与工程化

- 模块化与包化：逐步引入 `pyproject.toml`，形成可安装的内核与应用包。
- 入口统一：提供明确的 CLI/Web 启动入口与配置模板。
- 插件接口：定义解析器/索引器的扩展协议，降低新增功能成本。

## 2. 数据层演进

- Catalog schema v2：更多字段归一化（prefab、asset、tuning trace）。
- 增量构建：对比 scripts hash，支持局部重建与 cache reuse。
- 存储升级：从 JSON 过渡到 SQLite/Parquet（大规模检索性能）。

## 3. WebCraft 体验

- 多维检索：标签、来源、制作链路、组件属性联动检索。
- 探索/模拟：料理食材驱动探索、配方模拟与发现流。
- 食材索引：解析 ingredients/cooking 定义，提供 cooking_ingredients tags 数据契约。
- 信息密度：表格/列表切换，中英文/调试 ID 同屏，快捷复制。
- 结果解释：TUNING 解析链路可视化、配方链路图与条件展示。
- 体验与性能：统一页面结构、键盘/移动端优化、静态资源本地化与缓存。

## 4. CLI 与工具链

- CLI 统一输出规范（JSON/表格/纯文本）。
- devtools 统一日志与报告产出格式，便于对比与自动化。
- 建立脚手架：新工具生成器（模板 + 注册）。

## 5. 质量与可观测

- 核心功能最小测试集：解析器、索引器、Web API 合同测试。
- 产物验证：索引一致性检查（assets/recipes/cooking）。
- 运行指标：构建时间、产物规模、缺失率统计。

## 6. 生态与协作

- 明确贡献指南与代码风格约定。
- 对外文档与示例数据集（便于复现与扩展）。
- 分离实验区与稳定区（feature branch/experimental modules）。
