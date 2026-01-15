#!/usr/bin/env python3
"""
Wagstaff-Lab 工具注册中心 (v2.3)
"""

TOOLS = [
    # --- CLI 工具 (apps/cli) ---
    {
        "file": "guide.py",
        "alias": None,
        "desc": "Wagstaff-Lab 控制台主面板",
        "usage": "Wagstaff-Lab",
        "type": "CLI"
    },
    {
        "file": "doctor.py",
        "alias": "doctor",
        "desc": "环境配置与依赖健康检查",
        "usage": "wagstaff doctor",
        "type": "CLI"
    },
    {
        "file": "wiki.py",
        "alias": "wiki",
        "desc": "物品/配方/数值查询百科",
        "usage": "wagstaff wiki <item_code>",
        "type": "CLI"
    },
    {
        "file": "explorer.py",
        "alias": "exp",
        "desc": "源码结构浏览与深度分析",
        "usage": "wagstaff exp",
        "type": "CLI"
    },

    # --- 开发工具 (devtools/) ---
    {
        "file": "pm.py",
        "alias": "pm",
        "desc": "项目进度与任务管理",
        "usage": "pm [ui|obj|add|done|log]",
        "type": "Dev",
        "folder": "devtools"
    },
    {
        "file": "reporter.py",
        "alias": "report",
        "desc": "生成全服资产/配方分布报告",
        "usage": "wagstaff report [assets|recipes|all]",
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
        "file": "installer.py",
        "alias": "install",
        "desc": "环境注册与安装向导",
        "usage": "python3 devtools/installer.py",
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
        "file": "codemap.py",
        "alias": "map",
        "desc": "生成 DST scripts 宏观结构地图报告",
        "usage": "wagstaff map",
        "type": "Dev",
        "folder": "devtools"
    },
]

def get_tools():
    return TOOLS
