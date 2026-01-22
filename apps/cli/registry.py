#!/usr/bin/env python3
"""Wagstaff-Lab 工具注册中心."""

TOOLS = [
    # --- CLI 工具 (apps/cli) ---
    {
        "file": "dash.py",
        "alias": "dash",
        "desc": "Wagstaff-Lab 控制台主面板",
        "usage": "wagstaff dash",
        "type": "CLI",
        "folder": "apps/cli/commands"
    },
    {
        "file": "doctor.py",
        "alias": "doctor",
        "desc": "环境配置与依赖健康检查",
        "usage": "wagstaff doctor",
        "type": "CLI",
        "folder": "apps/cli/commands"
    },
    {
        "file": "wiki.py",
        "alias": "wiki",
        "desc": "物品/配方/数值查询百科",
        "usage": "wagstaff wiki <item_code>",
        "type": "CLI",
        "folder": "apps/cli/commands"
    },
    {
        "file": "explorer.py",
        "alias": "exp",
        "desc": "源码结构浏览与深度分析",
        "usage": "wagstaff exp",
        "type": "CLI",
        "folder": "apps/cli/commands"
    },
    {
        "file": "mgmt.py",
        "alias": "mgmt",
        "desc": "项目管理：状态展示与同步",
        "usage": "wagstaff mgmt <status|sync|dump|check>",
        "type": "CLI",
        "folder": "apps/cli/commands"
    },
    {
        "file": "server.py",
        "alias": "server",
        "desc": "DST 服务器管理 (screen-based)",
        "usage": "wagstaff server <status|start|stop|restart|update|backup|restore|logs|cmd|ui>",
        "type": "CLI",
        "folder": "apps/cli/commands"
    },

    # --- 开发工具 (devtools/) ---
    {
        "file": "report_hub.py",
        "alias": "report",
        "desc": "报告中心：build/list/open",
        "usage": "wagstaff report [build|list|open] [--all] [--stats-gap]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "portal_hub.py",
        "alias": "portal",
        "desc": "聚合视图：管理 + 报告 + 质量",
        "usage": "wagstaff portal [build|list|open]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_catalog_v2.py",
        "alias": "catalog2",
        "desc": "生成 Catalog v2 (item-centric)",
        "usage": "wagstaff catalog2 [--dst-root PATH] [--tuning-mode value_only|full] [--tuning-trace-out PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_catalog_sqlite.py",
        "alias": "catalog-sqlite",
        "desc": "生成 Catalog SQLite v4",
        "usage": "wagstaff catalog-sqlite [--catalog PATH] [--out PATH] [--tuning-trace PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_i18n_index.py",
        "alias": "i18n",
        "desc": "生成 i18n 索引 (names + UI strings)",
        "usage": "wagstaff i18n [--lang zh] [--dst-root PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_farming_defs.py",
        "alias": "farming-defs",
        "desc": "生成耕种机制索引 (farming defs)",
        "usage": "wagstaff farming-defs [--dst-root PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "farming_sim.py",
        "alias": "farming-sim",
        "desc": "耕种模拟（轻量，基于 farming defs）",
        "usage": "wagstaff farming-sim <plant_id> [--season autumn] [--stress 0]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_icons.py",
        "alias": "icons",
        "desc": "生成物品图标 PNG + icon index",
        "usage": "wagstaff icons [--dst-root PATH] [--all-elements]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_catalog_index.py",
        "alias": "catindex",
        "desc": "生成 Catalog 紧凑索引（列表 + 多维倒排）",
        "usage": "wagstaff catindex [--catalog PATH] [--icon-index PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_mechanism_index.py",
        "alias": "mechanism-index",
        "desc": "生成机制索引（组件 + prefab 关系）",
        "usage": "wagstaff mechanism-index [build|validate|diff] ...",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_behavior_graph.py",
        "alias": "behavior-graph",
        "desc": "生成行为图谱索引（stategraph + brain）",
        "usage": "wagstaff behavior-graph [--dst-root PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_index_manifest.py",
        "alias": "index-manifest",
        "desc": "生成索引版本清单 (manifest)",
        "usage": "wagstaff index-manifest [--out PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "quality_gate.py",
        "alias": "quality",
        "desc": "质量门禁自检（默认仅提示）",
        "usage": "wagstaff quality [--enforce] [--strict]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "snapshot.py",
        "alias": "snap",
        "desc": "生成 LLM 友好代码快照",
        "usage": "wagstaff snap [-h] [--mode {llm,core,archive,custom}] [--template TEMPLATE] [--config CONFIG] [--output OUTPUT] [--focus PATH|GLOB ...] [--list-templates] [--no-redact] [--zip] [--no-tree] [--no-inventory] [--no-contents] [--no-stats] [--verbose] [--plan]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "sampler.py",
        "alias": "samples",
        "desc": "生成 DST Lua 样本包（用于扩展解析器）",
        "usage": "wagstaff samples [--categories ...] [--n N] [--head-lines N] ...",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_resource_index.py",
        "alias": "resindex",
        "desc": "生成 DST 资源索引（scripts + data）",
        "usage": "wagstaff resindex [--data-full] [--bundle-full] [--dst-root PATH]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "serve_webcraft.py",
        "alias": "web",
        "desc": "启动 WebCraft (FastAPI + Uvicorn)",
        "usage": "wagstaff web [--host 0.0.0.0 --port 20000]",
        "type": "Dev",
        "folder": "devtools"
    },
]

def get_tools():
    return TOOLS
