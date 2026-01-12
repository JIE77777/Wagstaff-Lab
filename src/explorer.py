#!/usr/bin/env python3
import os
import zipfile
import sys
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.syntax import Syntax
from rich import box

# === 引入 Wagstaff 工具库 ===
# 将 src 目录加入路径，以便导入 utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import wagstaff_config

# 初始化 Rich
console = Console()

class DSTExplorer:
    def __init__(self):
        # 从统一配置读取路径
        self.base_dir = wagstaff_config.get('PATHS', 'DST_ROOT')
        self.zip_path = os.path.join(self.base_dir, "data", "databundles", "scripts.zip")
        self.fallback_dir = os.path.join(self.base_dir, "data", "scripts")
        
        self.mode = None 
        self.source = None
        self.file_list = []
        self.root_prefix = "scripts/" 
        
        self.init_source()

    def init_source(self):
        console.print(Panel(f"[bold cyan]Wagstaff 源码透视镜 v2.1[/bold cyan]\n目标源: {self.base_dir}", border_style="blue"))

        if os.path.exists(self.zip_path):
            self.mode = 'zip'
            self.source = zipfile.ZipFile(self.zip_path, 'r')
            self.file_list = self.source.namelist()
            console.print(f"[green]✅ 已挂载 ZIP 核心: scripts.zip ({len(self.file_list)} files)[/green]")
        elif os.path.exists(self.fallback_dir):
            self.mode = 'folder'
            self.source = self.fallback_dir
            for root, _, files in os.walk(self.fallback_dir):
                for name in files:
                    rel_path = os.path.relpath(os.path.join(root, name), self.fallback_dir)
                    self.file_list.append(rel_path)
            console.print(f"[green]✅ 已挂载文件夹: scripts/ ({len(self.file_list)} files)[/green]")
        else:
            console.print(f"[bold red]❌ 致命错误：在 {self.base_dir} 未找到 scripts 数据！[/bold red]")
            console.print("请检查 conf/settings.ini 配置是否正确。")
            sys.exit(1)

    def get_structure_tree(self):
        tree = Tree(f"📁 [bold yellow]源码结构 ({self.mode})[/bold yellow]")
        dir_counts = {}
        for f in self.file_list:
            clean_path = f.replace(self.root_prefix, "", 1) if f.startswith(self.root_prefix) else f
            top_dir = clean_path.split('/')[0] if '/' in clean_path else "[Root Files]"
            dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

        for d, count in sorted(dir_counts.items(), key=lambda x: x[1], reverse=True):
            if d == "[Root Files]":
                tree.add(f"📄 {d} ({count})")
            else:
                style = "bold cyan" if d in ["prefabs", "components", "tuning.lua"] else "white"
                tree.add(f"📂 [{style}]{d}[/{style}] ([dim]{count}[/dim])")
        return tree

    def search_files(self):
        keyword = Prompt.ask("[bold green]🔍 搜索关键词[/bold green]")
        if not keyword: return
        matches = [f for f in self.file_list if keyword.lower() in f.lower()]
        
        if not matches:
            console.print("[yellow]无结果[/yellow]")
            return

        table = Table(title=f"Results: '{keyword}'", box=box.SIMPLE)
        table.add_column("路径", style="dim")
        table.add_column("文件", style="bold green")
        for m in matches[:15]:
            d, f = os.path.split(m)
            table.add_row(d, f)
        console.print(table)
        if len(matches) > 15: console.print(f"[dim]...剩余 {len(matches)-15} 项隐藏[/dim]")

    def read_content(self, filepath):
        try:
            if self.mode == 'zip':
                with self.source.open(filepath) as f: return f.read().decode('utf-8', errors='replace')
            else:
                with open(os.path.join(self.source, filepath), 'r', encoding='utf-8') as f: return f.read()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

    def preview_file(self):
        target = Prompt.ask("[bold green]👀 文件名[/bold green]")
        candidates = [f for f in self.file_list if target.lower() in f.lower()]
        if not candidates: return console.print("[red]未找到[/red]")
        
        target_file = candidates[0]
        if len(candidates) > 1: console.print(f"[yellow]打开最匹配项: {target_file}[/yellow]")
        
        content = self.read_content(target_file)
        if content:
            syntax = Syntax("\n".join(content.splitlines()[:50]), "lua", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"{target_file} (Top 50 lines)", border_style="blue"))
            input("按回车继续...")

    def show_tuning(self):
        path = f"{self.root_prefix}tuning.lua"
        if path not in self.file_list: path = "tuning.lua"
        
        content = self.read_content(path)
        if not content: return console.print("[red]Tuning.lua not found[/red]")
        
        console.print("[bold magenta]🔢 Tuning 数值采样[/bold magenta]")
        count = 0
        for line in content.splitlines():
            line = line.strip()
            if ' = ' in line and line[0].isupper() and "--" not in line:
                console.print(f"  [cyan]{line}[/cyan]")
                count += 1
                if count >= 10: break

def main():
    explorer = DSTExplorer()
    while True:
        console.print("\n[bold white on blue] 🦁 Wagstaff 探索面板 [/bold white on blue]")
        console.print("1. [bold]📁 结构[/]  2. [bold]🔍 搜索[/]  3. [bold]👀 预览[/]  4. [bold]🔢 数值[/]  0. [bold red]退出[/]")
        choice = IntPrompt.ask("选择", choices=["0","1","2","3","4"], default=1)
        if choice == 0: break
        elif choice == 1: console.print(explorer.get_structure_tree())
        elif choice == 2: explorer.search_files()
        elif choice == 3: explorer.preview_file()
        elif choice == 4: explorer.show_tuning()

if __name__ == "__main__":
    main()
