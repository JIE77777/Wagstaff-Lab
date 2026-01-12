#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from rich.console import Console

# 引入注册表
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from registry import get_tools

console = Console()

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
BIN_DIR = PROJECT_ROOT / "bin"
SRC_DIR = PROJECT_ROOT / "src"
DEV_DIR = PROJECT_ROOT / "devtools"

def get_shell_config():
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell: return home / ".zshrc"
    elif "bash" in shell: return home / ".bashrc"
    else: return home / ".profile"

def create_wrappers():
    # 1. 创建 'Wagstaff-Lab' 主入口
    main_wrapper = BIN_DIR / "Wagstaff-Lab"
    with open(main_wrapper, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'python3 "{SRC_DIR}/guide.py" "$@"\n')
    os.chmod(main_wrapper, 0o755)
    
    # 2. 创建 'pm' 快捷指令
    pm_wrapper = BIN_DIR / "pm"
    with open(pm_wrapper, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'python3 "{DEV_DIR}/pm.py" "$@"\n')
    os.chmod(pm_wrapper, 0o755)

    # 3. 动态创建 'wagstaff' 工具箱 (基于 Registry)
    ws_wrapper = BIN_DIR / "wagstaff"
    with open(ws_wrapper, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('TOOL=$1\nshift\n')
        f.write('case "$TOOL" in\n')
        
        # --- 动态生成 Case 分支 ---
        tools = get_tools()
        registered_aliases = []
        
        for tool in tools:
            alias = tool.get('alias')
            if not alias: continue # 跳过没有别名的工具
            
            folder = tool.get('folder', 'src')
            # 转换 folder 为绝对路径变量
            if folder == 'src': abs_path = SRC_DIR
            elif folder == 'devtools': abs_path = DEV_DIR
            else: abs_path = PROJECT_ROOT / folder
            
            f.write(f'  {alias}) python3 "{abs_path}/{tool["file"]}" "$@" ;;\n')
            registered_aliases.append(f"{alias} ({tool['desc']})")
        # ------------------------

        f.write(f'  *) "{main_wrapper}" "$@" ;;\n') 
        f.write('esac\n')
    os.chmod(ws_wrapper, 0o755)
    
    console.print(f"[green]✅ 指令注册成功 (Registry Driven)[/green]")
    console.print(f"   已自动注册 {len(registered_aliases)} 个子命令到 'wagstaff'")

def register_to_path():
    rc_file = get_shell_config()
    bin_path_str = str(BIN_DIR)
    
    if not rc_file.exists(): return

    content = rc_file.read_text()
    if f'export PATH="{bin_path_str}:$PATH"' in content:
        console.print("[dim]⚡ 环境变量已就绪[/dim]")
    else:
        try:
            with open(rc_file, 'a') as f:
                f.write(f'\n# Wagstaff-Lab Environment\nexport PATH="{bin_path_str}:$PATH"\n')
            console.print(f"[green]✅ PATH 已更新[/green]")
        except Exception:
            pass

def main():
    console.print("[bold blue]🔧 Wagstaff-Lab 自动化注册中心[/bold blue]")
    create_wrappers()
    register_to_path()

if __name__ == "__main__":
    main()
