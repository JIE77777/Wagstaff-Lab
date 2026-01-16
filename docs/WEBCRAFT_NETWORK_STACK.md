# WebCraft 网络基建（FastAPI/ASGI）

目标：把 Web/GUI Craft 从“临时 stdlib server”升级为可扩展的系统级服务基座。

## 选型
- ASGI 框架：FastAPI
- 服务器：Uvicorn
- 中间件：GZip、可选 CORS
- 数据源：data/index/wagstaff_catalog_v2.json（item-centric 索引产物）

## 目录结构
- apps/webcraft/
  - app.py          FastAPI app factory
  - api.py          REST API 路由（/api/v1）
  - catalog_store.py  catalog 装载 + 内存索引
  - planner.py      craft planner（inventory -> craftable/missing）
  - ui.py           单页 UI（零构建）
  - settings.py     配置结构

- devtools/serve_webcraft.py  开发/部署启动器

## 启动
```bash
python3 devtools/serve_webcraft.py --host 0.0.0.0 --port 20000 --no-open
```

## 反向代理挂载（root_path）
若挂载在 /webcraft：
```bash
python3 devtools/serve_webcraft.py --root-path /webcraft --host 0.0.0.0 --port 20000
```

UI 与 API 都使用相同 root_path 前缀，前端以相对路径访问 `/api/v1/...`，避免 0.0.0.0 导致的跨机器交互失败。

## API
- GET /api/v1/meta
- GET /api/v1/craft/filters
- GET /api/v1/craft/tabs
- GET /api/v1/craft/tags
- GET /api/v1/craft/recipes/search?q=...
- GET /api/v1/craft/recipes/{name}
- POST /api/v1/craft/plan
- POST /api/v1/craft/missing

## 后续扩展建议
- 引入 “station/tech/skill tree” 规则：只扩展 planner + API，不改 UI 架构
- catalog 改为 SQLite：CatalogStore 层替换为 SQLiteStore（API/UI 无需变化）
- 加 websocket/SSE：用于索引重建、长任务进度推送
