#!/usr/bin/env python3
import os
import platform
import subprocess
import shutil
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "project_context.txt"

SCAN_RULES = [
    {"dir": "bin", "ext": ".sh"},
    {"dir": "src", "ext": ".py"},
    {"dir": "conf", "ext": ".ini"},
    {"dir": "devtools", "ext": ".py"},
    {"dir": ".", "ext": ".md"},
    {"dir": ".", "ext": ".txt"},
]

IGNORE_DIRS = {".git", "__pycache__", "logs", "env", "venv", ".idea", ".vscode"}
IGNORE_FILES = {"project_context.txt", ".DS_Store", "id_rsa", "known_hosts"}

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "Unknown"

def get_system_fingerprint():
    info = []
    info.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    info.append(f"User: {os.getenv('USER', 'Unknown')}")
    info.append(f"Host: {platform.node()} ({platform.system()} {platform.release()})")
    info.append(f"Python: {platform.python_version()} ({sys.executable})")
    try:
        import rich
        ver = getattr(rich, '__version__', 'Installed (ver unknown)')
        info.append(f"Rich Ver: {ver}")
    except:
        info.append("Rich Ver: Not Installed")
    return "\n".join(info)

def get_git_status():
    if not (PROJECT_ROOT / ".git").exists(): return "Git: Not a repository"
    branch = run_cmd("git rev-parse --abbrev-ref HEAD")
    commit = run_cmd("git rev-parse --short HEAD")
    last_msg = run_cmd("git log -1 --pretty=%B")
    is_dirty = run_cmd("git status --porcelain") != ""
    dirty_mark = " [DIRTY]" if is_dirty else " [CLEAN]"
    return f"Branch: {branch}{dirty_mark}\nCommit: {commit}\nMessage: {last_msg}"

def generate_tree(dir_path, prefix=""):
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
    print(f"📸 正在生成 Wagstaff-Lab 全息快照...")
    report = []
    report.append("# Wagstaff-Lab Project Snapshot")
    
    report.append("\n## 1. Environment Diagnostics")
    report.append("```yaml")
    report.append(get_system_fingerprint())
    report.append("-" * 20)
    report.append(get_git_status())
    report.append("```")

    report.append("\n## 2. Project Structure")
    report.append("```text")
    report.append(generate_tree(PROJECT_ROOT))
    report.append("```")

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
            if lang == 'ini': lang = 'toml'
            report.append(f"```{lang}")
            try:
                report.append(file_path.read_text(encoding='utf-8'))
                file_count += 1
            except:
                report.append("Error reading file")
            report.append("```")
    
    # Section 4: Project Context (Auto-Generated)
    report.append("\n## 4. Project Context (Auto-Generated)")
    report.append("```text")
    if os.path.exists("PROJECT_STATUS.json"):
        try:
            with open("PROJECT_STATUS.json", 'r') as f:
                data = json.load(f)
                if data.get("guidelines"):
                    report.append("DEV MANIFESTO:")
                    for rule in data["guidelines"]:
                        report.append(f"* {rule}")
                    report.append("-" * 20)
                report.append(f"OBJECTIVE: {data.get('objective')}")
                report.append("\nTASKS:")
                for i, t in enumerate(data.get('tasks', [])):
                    mark = "[x]" if t['status'] == 'done' else "[ ]"
                    report.append(f"{i}. {mark} {t['desc']}")
        except:
            report.append("Error reading project status.")
    else:
        report.append("No project status file found.")
    report.append("```")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print(f"✅ 快照生成完毕: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
