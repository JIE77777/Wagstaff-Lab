#!/usr/bin/env python3
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.syntax import Syntax
from rich import box
from engine import WagstaffEngine

console = Console()

class DSTExplorer:
    def __init__(self):
        # 直接使用引擎，不再自己处理 Zip 和 Tuning
        try:
            self.engine = WagstaffEngine(load_db=True)
        except Exception as e:
            console.print(f"[red]引擎启动失败: {e}[/red]")
            sys.exit(1)
        
        console.print(Panel(f"[bold cyan]Wagstaff 源码透视镜 v3.0[/bold cyan]\n核心: {self.engine.mode.upper()} 模式", border_style="blue"))
        if self.engine.tuning:
            console.print(f"[dim]⚡ Tuning 解析器就绪 (包含 {len(self.engine.tuning.raw_map)} 条常数)[/dim]")

    def get_structure_tree(self):
        tree = Tree(f"📁 [bold yellow]源码结构[/bold yellow]")
        dir_counts = {}
        for f in self.engine.file_list:
            clean_path = f.replace("scripts/", "", 1) if f.startswith("scripts/") else f
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
        matches = [f for f in self.engine.file_list if keyword.lower() in f.lower()]
        
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

    def analyze_content(self, filename, content):
        # 使用引擎提供的分析方法 (已包含数值增强)
        # 注意：engine.analyze_prefab 是针对 prefab 的，这里我们可能需要通用的 analyzer
        # 为了复用 engine 的能力，我们手动调用 analyzer 但使用 engine 的 tuning
        from analyzer import LuaAnalyzer
        
        try:
            analyzer = LuaAnalyzer(content)
            data = analyzer.get_report()
        except Exception as e:
            console.print(f"[red]解析失败: {e}[/red]")
            return
        
        tree = Tree(f"🧬 [bold green]深度解析: {filename}[/bold green]")
        
        # 1. 资源
        if data.get('assets'):
            asset_branch = tree.add(f"📦 资源引用 ({len(data['assets'])})")
            for a in data['assets']:
                style = "magenta" if "Anim" in a['type'] else "blue"
                asset_branch.add(f"[{style}]{a['type']}[/{style}]: {a['path']}")

        # 2. 逻辑 (Brain/StateGraph/Tags)
        logic_branch = tree.add("🧠 核心逻辑")
        has_logic = False
        if data.get('brain'): 
            logic_branch.add(f"AI: [magenta]{data['brain']}[/magenta]")
            has_logic = True
        if data.get('stategraph'): 
            logic_branch.add(f"SG: [magenta]{data['stategraph']}[/magenta]")
            has_logic = True
        if data.get('tags'): 
            tags = data['tags']
            tag_str = ", ".join([f"[dim]{t}[/dim]" for t in tags[:8]])
            if len(tags) > 8: tag_str += "..."
            logic_branch.add(f"Tags: {tag_str}")
            has_logic = True
        if not has_logic: logic_branch.label = "[dim]🧠 核心逻辑 (无)[/dim]"

        # 3. 组件 (使用 Engine 的 Tuning 进行增强)
        if data.get('components'):
            comp_branch = tree.add(f"⚙️ 功能组件 ({len(data['components'])})")
            for comp in data['components']:
                node = comp_branch.add(f"[bold yellow]{comp['name']}[/bold yellow]")
                
                # 属性
                if comp['properties']:
                    target = node if len(comp['properties']) <=3 else node.add("[dim]属性配置[/dim]")
                    for p in comp['properties']:
                        p = self.engine.tuning.enrich(p) if self.engine.tuning else p
                        if "=" in p:
                            k, v = p.split("=", 1)
                            target.add(f"[cyan]{k.strip()}[/cyan] = [white]{v.strip()}[/white]")
                        else:
                            target.add(f"[cyan]{p}[/cyan]")
                
                # 方法
                if comp['methods']:
                    target = node if len(comp['methods']) <=3 else node.add("[dim]函数调用[/dim]")
                    for m in comp['methods']:
                        m = self.engine.tuning.enrich(m) if self.engine.tuning else m
                        target.add(f"[green]ƒ[/green] {m}")
        else:
            tree.add("[dim]⚙️ 功能组件 (无)[/dim]")

        console.print(Panel(tree, border_style="green"))
        input("按回车返回...")

    def preview_file(self):
        target = Prompt.ask("[bold green]👀 文件名[/bold green]")
        path = self.engine.find_file(target, fuzzy=True)
        if not path:
            console.print("[red]未找到[/red]")
            return
        
        console.print(f"[yellow]打开: {path}[/yellow]")
        content = self.engine.read_file(path)
        
        if content:
            syntax = Syntax("\n".join(content.splitlines()[:50]), "lua", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"{path} (Top 50 lines)", border_style="blue"))
            
            action = Prompt.ask("[bold cyan]下一步[/bold cyan]", choices=["q", "a"], default="q")
            if action == "a":
                self.analyze_content(path, content)

    def show_tuning(self):
        if not self.engine.tuning: 
            return console.print("[red]Tuning 未加载[/red]")
        
        console.print("[bold magenta]🔢 Tuning 数值采样[/bold magenta]")
        # 简单展示前 10 个
        count = 0
        for k, v in list(self.engine.tuning.raw_map.items())[:10]:
             console.print(f"  [cyan]{k}[/cyan] = {v}")
             count += 1

def main():
    explorer = DSTExplorer()
    while True:
        console.print("\n[bold white on blue] 🦁 Wagstaff 探索面板 v3.0 [/bold white on blue]")
        console.print("1. [bold]📁 结构[/]  2. [bold]🔍 搜索[/]  3. [bold]👀 预览&分析[/]  4. [bold]🔢 数值[/]  0. [bold red]退出[/]")
        choice = IntPrompt.ask("选择", choices=["0","1","2","3","4"], default=1)
        if choice == 0: break
        elif choice == 1: console.print(explorer.get_structure_tree())
        elif choice == 2: explorer.search_files()
        elif choice == 3: explorer.preview_file()
        elif choice == 4: explorer.show_tuning()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
