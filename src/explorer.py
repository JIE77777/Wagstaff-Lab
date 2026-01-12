#!/usr/bin/env python3
import os
import zipfile
import fnmatch
import sys
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.syntax import Syntax
from rich import box

# 初始化 Rich 终端
console = Console()

# ================= 配置 =================
BASE_DIR = os.path.expanduser("~/dontstarvetogether_dedicated_server")
ZIP_PATH = os.path.join(BASE_DIR, "data", "databundles", "scripts.zip")
FALLBACK_DIR = os.path.join(BASE_DIR, "data", "scripts")

class DSTExplorer:
    def __init__(self):
        self.mode = None # 'zip' or 'folder'
        self.source = None
        self.file_list = []
        self.root_prefix = "scripts/" # 修正：这是我们在压缩包里发现的根目录前缀
        
        self.init_source()

    def init_source(self):
        """初始化数据源，优先读取 ZIP"""
        console.print(Panel(f"[bold cyan]DST 源码资源管理器 v2.0[/bold cyan]\n目标路径: {BASE_DIR}", border_style="blue"))

        if os.path.exists(ZIP_PATH):
            self.mode = 'zip'
            self.source = zipfile.ZipFile(ZIP_PATH, 'r')
            self.file_list = self.source.namelist()
            console.print(f"[green]✅ 成功挂载 scripts.zip ({len(self.file_list)} 个文件)[/green]")
        elif os.path.exists(FALLBACK_DIR):
            self.mode = 'folder'
            self.source = FALLBACK_DIR
            # 递归获取文件列表
            for root, _, files in os.walk(FALLBACK_DIR):
                for name in files:
                    rel_path = os.path.relpath(os.path.join(root, name), FALLBACK_DIR)
                    self.file_list.append(rel_path)
            console.print(f"[green]✅ 成功挂载 scripts 文件夹 ({len(self.file_list)} 个文件)[/green]")
        else:
            console.print("[bold red]❌ 致命错误：找不到 scripts.zip 或 scripts 文件夹！[/bold red]")
            sys.exit(1)

    def get_structure_tree(self):
        """生成目录树视图"""
        tree = Tree(f"📁 [bold yellow]DST 源码结构 ({self.mode})[/bold yellow]")
        
        # 统计顶层目录
        dir_counts = {}
        for f in self.file_list:
            # 移除前缀 scripts/
            clean_path = f.replace(self.root_prefix, "", 1) if f.startswith(self.root_prefix) else f
            top_dir = clean_path.split('/')[0]
            
            # 如果是文件（没有 /），归类为 [Root Files]
            if '/' not in clean_path:
                top_dir = "[Root Files]"
            
            dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

        # 排序并添加到树
        for d, count in sorted(dir_counts.items(), key=lambda item: item[1], reverse=True):
            if d == "[Root Files]":
                tree.add(f"📄 {d} ({count} 个文件)")
            else:
                # 重点高亮核心文件夹
                style = "bold cyan" if d in ["prefabs", "components", "tuning.lua"] else "white"
                tree.add(f"📂 [{style}]{d}[/{style}] ([dim]{count}[/dim])")
        
        return tree

    def search_files(self):
        """搜索文件功能"""
        keyword = Prompt.ask("[bold green]🔍 请输入搜索关键词 (例如: klaus, spear)[/bold green]")
        if not keyword: return

        matches = []
        for f in self.file_list:
            if keyword.lower() in f.lower():
                matches.append(f)
        
        if not matches:
            console.print("[yellow]未找到匹配文件。[/yellow]")
            return

        table = Table(title=f"搜索结果: '{keyword}'", box=box.SIMPLE)
        table.add_column("路径", style="dim")
        table.add_column("文件名", style="bold green")

        # 只显示前 15 个
        for m in matches[:15]:
            dirname, filename = os.path.split(m)
            table.add_row(dirname, filename)
        
        console.print(table)
        if len(matches) > 15:
            console.print(f"[dim]... 还有 {len(matches)-15} 个结果未显示[/dim]")

    def read_file_content(self, filepath):
        """读取并高亮显示文件内容"""
        try:
            content = ""
            if self.mode == 'zip':
                with self.source.open(filepath) as f:
                    content = f.read().decode('utf-8', errors='replace')
            else:
                real_path = os.path.join(self.source, filepath)
                with open(real_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            return content
        except Exception as e:
            console.print(f"[red]读取失败: {e}[/red]")
            return None

    def preview_file(self):
        """预览指定文件"""
        target = Prompt.ask("[bold green]👀 输入要查看的文件名 (支持模糊匹配，如 tuning.lua)[/bold green]")
        
        # 模糊查找最匹配的文件
        candidates = [f for f in self.file_list if target.lower() in f.lower()]
        
        if not candidates:
            console.print("[red]❌ 找不到文件[/red]")
            return
        
        # 如果有多个，让用户选；如果只有一个，直接打开
        selected_file = candidates[0]
        if len(candidates) > 1:
            console.print(f"[yellow]找到 {len(candidates)} 个文件，默认打开第一个:[/yellow] {selected_file}")
            # 这里为了简便直接开第一个，你可以做个列表让用户选
        
        content = self.read_file_content(selected_file)
        if content:
            # 只显示前 50 行，避免刷屏
            lines = content.splitlines()
            preview_lines = "\n".join(lines[:50])
            
            console.print(Panel(f"文件: {selected_file} (前 50 行)", style="bold blue"))
            # 使用 Rich 的语法高亮
            syntax = Syntax(preview_lines, "lua", theme="monokai", line_numbers=True)
            console.print(syntax)
            console.print("[dim]--- (按回车继续) ---[/dim]")
            input()

    def show_tuning_sample(self):
        """专门展示 Tuning.lua 的关键数值"""
        # 修正：现在我们要加上 scripts/ 前缀来找 tuning.lua
        tuning_path = f"{self.root_prefix}tuning.lua"
        
        if tuning_path not in self.file_list:
             # 尝试不带前缀
             tuning_path = "tuning.lua"
             if tuning_path not in self.file_list:
                console.print("[red]❌ 无法定位 tuning.lua[/red]")
                return

        content = self.read_file_content(tuning_path)
        if not content: return

        console.print("[bold magenta]🔢 全局数值预览 (tuning.lua)[/bold magenta]")
        # 简单提取几行大写的赋值语句
        count = 0
        for line in content.splitlines():
            line = line.strip()
            # 匹配大写字母开头的赋值，如 WILBUR_RUN_SPEED = 5.5
            if ' = ' in line and line[0].isupper() and "--" not in line:
                console.print(f"  [cyan]{line}[/cyan]")
                count += 1
                if count >= 10: break
        console.print("[dim]... (数值系统包含数千个变量)[/dim]")

# ================= 主菜单 =================
def main():
    explorer = DSTExplorer()
    
    while True:
        console.print("\n[bold white on blue] 🦁 DST 探索者菜单 [/bold white on blue]")
        console.print("1. [bold]📁 查看目录结构[/bold] (宏观视角)")
        console.print("2. [bold]🔍 搜索文件[/bold] (查找逻辑位置)")
        console.print("3. [bold]👀 预览源码[/bold] (读取代码)")
        console.print("4. [bold]🔢 抽查 Tuning 数值[/bold] (查看平衡性参数)")
        # ⬇️ 修复了这一行：把 [/bold] 改成了 [/]
        console.print("0. [bold red]退出[/]")
        
        choice = IntPrompt.ask("请选择", choices=["0", "1", "2", "3", "4"], default=1)
        
        if choice == 0:
            console.print("[yellow]👋 See you in the Constant![/yellow]")
            break
        elif choice == 1:
            console.print(explorer.get_structure_tree())
        elif choice == 2:
            explorer.search_files()
        elif choice == 3:
            explorer.preview_file()
        elif choice == 4:
            explorer.show_tuning_sample()
        
        console.print("\n" + "-"*30)

if __name__ == "__main__":
    main()
