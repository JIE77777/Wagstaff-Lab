#!/usr/bin/env python3
import os
import platform
import subprocess
import shutil
import sys
import json
from pathlib import Path
from datetime import datetime

# ================= 配置区 =================
# 自动定位项目根目录 (devtools 的上一级)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "project_context.txt"

# 自动扫描规则
SCAN_RULES = [
    {"dir": "bin", "ext": ".sh"},
    {"dir": "src", "ext": ".py"},
    {"dir": "conf", "ext": ".ini"},
    {"dir": "devtools", "ext": ".py"},
    {"dir": ".", "ext": ".md"},      # README.md
    {"dir": ".", "ext": ".txt"},     # requirements.txt
]

# 忽略列表
IGNORE_DIRS = {".git", "__pycache__", "logs", "env", "venv", ".idea", ".vscode"}
IGNORE_FILES = {"project_context.txt", ".DS_Store", "id_rsa", "known_hosts"}

# ================= 功能函数 =================

def run_cmd(cmd):
    """执行 Shell 命令并返回结果"""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "Unknown"

def get_system_fingerprint():
    """获取详细的环境指纹 (System Fingerprint)"""
    info = []
    
    # 1. 基础信息
    info.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    info.append(f"User: {os.getenv('USER', 'Unknown')}")
    info.append(f"Host: {platform.node()} ({platform.system()} {platform.release()})")
    
    # 2. Python 环境
    info.append(f"Python: {platform.python_version()} ({sys.executable})")
    conda_env = os.getenv('CONDA_DEFAULT_ENV')
    if conda_env:
        info.append(f"Conda Env: {conda_env}")
    
    # 3. 依赖库检查 (修复了这里)
    try:
        import rich
        # 尝试获取版本，如果拿不到(AttributeError)则显示已安装但版本未知
        ver = getattr(rich, '__version__', 'Installed (ver unknown)')
        info.append(f"Rich Ver: {ver}")
    except ImportError:
        info.append("Rich Ver: Not Installed")
    except Exception as e:
        info.append(f"Rich Ver: Error ({str(e)})")

    # 4. 磁盘空间
    try:
        total, used, free = shutil.disk_usage(PROJECT_ROOT)
        free_gb = free // (2**30)
        total_gb = total // (2**30)
        usage_percent = round((used / total) * 100, 1)
        info.append(f"Disk: {free_gb}GB free / {total_gb}GB total ({usage_percent}% used)")
    except:
        info.append("Disk: Unavailable")
    
    return "\n".join(info)

def get_git_status():
    """获取版本控制状态"""
    if not (PROJECT_ROOT / ".git").exists():
        return "Git: Not a repository"
    
    branch = run_cmd("git rev-parse --abbrev-ref HEAD")
    commit = run_cmd("git rev-parse --short HEAD")
    last_msg = run_cmd("git log -1 --pretty=%B")
    
    # 检查是否有未提交的修改
    is_dirty = run_cmd("git status --porcelain") != ""
    dirty_mark = " [DIRTY]" if is_dirty else " [CLEAN]"
    
    return f"Branch: {branch}{dirty_mark}\nCommit: {commit}\nMessage: {last_msg}"

def generate_tree(dir_path, prefix=""):
    """递归生成目录树"""
    tree_str = ""
    try:
        contents = sorted([p for p in dir_path.iterdir() if p.name not in IGNORE_DIRS])
    except PermissionError:
        return f"{prefix}└── [Permission Denied]\n"

    pointers = [("├── " if i < len(contents) - 1 else "└── ") for i in range(len(contents))]
    
    for pointer, path in zip(pointers, contents):
        if path.name in IGNORE_FILES: continue
        
        tree_str += f"{prefix}{pointer}{path.name}\n"
        if path.is_dir():
            extension = "│   " if pointer == "├── " else "    "
            tree_str += generate_tree(path, prefix=prefix + extension)
    return tree_str

def main():
    print(f"📸 正在生成 Wagstaff-Lab 全息快照 (v2.1)...")
    
    report = []
    report.append("# Wagstaff-Lab Project Snapshot")
    
    # Section 1: 环境诊断
    report.append("\n## 1. Environment Diagnostics")
    report.append("```yaml")
    report.append(get_system_fingerprint())
    report.append("-" * 20)
    report.append(get_git_status())
    report.append("```")

    # Section 2: 目录结构
    report.append("\n## 2. Project Structure")
    report.append("```text")
    report.append(generate_tree(PROJECT_ROOT))
    report.append("```")

    # Section 3: 核心代码
    report.append("\n## 3. Source Code")
    
    file_count = 0
    for rule in SCAN_RULES:
        search_dir = PROJECT_ROOT / rule["dir"]
        if rule["dir"] == ".": search_dir = PROJECT_ROOT
            
        if not search_dir.exists(): continue
        
        for file_path in sorted(search_dir.glob(f"*{rule['ext']}")):
            if file_path.name in IGNORE_FILES: continue
            
            rel_path = file_path.relative_to(PROJECT_ROOT)
            report.append(f"\n### File: {rel_path}")
            
            lang = rule['ext'].replace('.', '')
            if lang == 'sh': lang = 'bash'
            if lang == 'ini': lang = 'toml'
            
            report.append(f"```{lang}")
            try:
                content = file_path.read_text(encoding='utf-8')
                report.append(content)
                file_count += 1
            except Exception as e:
                report.append(f"Error reading file: {e}")
            report.append("```")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print(f"✅ 快照生成完毕: {OUTPUT_FILE}")
    print(f"📊 已归档 {file_count} 个核心文件。")
    print("👉 运行 'cat project_context.txt' 查看。")

if __name__ == "__main__":
    main()
