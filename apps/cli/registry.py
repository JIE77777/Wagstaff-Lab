#!/usr/bin/env python3
"""
Wagstaff-Lab 工具注册中心 (v2.3)
"""

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
        "file": "reporter.py",
        "alias": "report",
        "desc": "生成全服资产/配方分布报告",
        "usage": "wagstaff report [assets|recipes|all]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "build_catalog_v2.py",
        "alias": "catalog2",
        "desc": "生成 Catalog v2 (item-centric)",
        "usage": "wagstaff catalog2 [--tuning-mode value_only|full] [--tuning-trace-out PATH]",
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
        "file": "catalog_quality.py",
        "alias": "catqa",
        "desc": "生成 Catalog 覆盖率/质量报告",
        "usage": "wagstaff catqa [--catalog PATH] [--i18n PATH] [--trace PATH]",
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
        "usage":  "wagstaff snapshot [-h] [--mode {llm,core,archive,custom}] [--template TEMPLATE] [--config CONFIG] [--output OUTPUT] [--focus PATH|GLOB ...] [--list-templates] [--no-redact] [--zip] [--no-tree] [--no-inventory] [--no-contents] [--no-stats] [--verbose] [--plan]",
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
        "file": "codemap.py",
        "alias": "map",
        "desc": "生成 DST scripts 宏观结构地图报告",
        "usage": "wagstaff map",
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
