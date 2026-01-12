#!/usr/bin/env python3
import os
from pathlib import Path

# === 核心配置 ===
# 定位项目根目录 (即 devtools 的上一级)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "project_context.txt"

# 需要读取详细内容的白名单 (相对路径)
# 这些文件会被完整打印出来，供 AI 分析
INCLUDE_FILES = [
    "bin/dst_tool.sh",       # 主控脚本
    "src/explorer.py",       # 探索器源码
    "src/wiki.py",           # (未来) 百科源码
    "conf/settings.ini",     # (未来) 配置文件
    "requirements.txt",      # 依赖列表
    "README.md"              # 项目说明
]

def generate_tree(dir_path, prefix=""):
    """生成目录树字符串 (忽略隐藏文件和垃圾文件)"""
    tree_str = ""
    try:
        # 获取目录下所有文件并排序
        contents = sorted(list(dir_path.iterdir()))
    except PermissionError:
        return f"{prefix}└── [Permission Denied]\n"

    # 过滤掉不需要显示的目录
    contents = [
        p for p in contents 
        if not p.name.startswith(('.', '__'))  # 忽略 .git, __pycache__
        and p.name != 'logs'                   # 忽略日志目录
    ]

    pointers = [("├── " if i < len(contents) - 1 else "└── ") for i in range(len(contents))]
    
    for pointer, path in zip(pointers, contents):
        tree_str += f"{prefix}{pointer}{path.name}\n"
        if path.is_dir():
            extension = "│   " if pointer == "├── " else "    "
            tree_str += generate_tree(path, prefix=prefix + extension)
    return tree_str

def main():
    print(f"📸 正在为 Wagstaff-Lab 生成项目快照...")
    report = []
    report.append("# Project Context Snapshot")
    report.append(f"Project Root: {PROJECT_ROOT}\n")
    
    # 1. 生成目录树
    report.append("## 1. Directory Structure")
    report.append("```text")
    report.append(generate_tree(PROJECT_ROOT))
    report.append("```\n")
    
    # 2. 读取关键文件内容
    report.append("## 2. Key File Contents")
    for rel_path in INCLUDE_FILES:
        file_path = PROJECT_ROOT / rel_path
        if file_path.exists():
            report.append(f"### File: {rel_path}")
            # 根据后缀名决定代码块的语言标记
            lang = file_path.suffix.replace('.', '') or 'text'
            if lang == 'sh': lang = 'bash'
            
            report.append(f"```{lang}")
            try:
                content = file_path.read_text(encoding='utf-8')
                report.append(content)
            except Exception as e:
                report.append(f"Error reading file: {e}")
            report.append("```\n")
        else:
            # 文件不存在时跳过，保持报告整洁，或者标记为未创建
            pass

    # 写入最终文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print(f"✅ 快照生成完毕: {OUTPUT_FILE}")
    print("👉 请使用 'cat project_context.txt' 查看并复制全部内容给 AI。")

if __name__ == "__main__":
    main()
