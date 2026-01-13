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
        # 初始化引擎
        try:
            self.engine = WagstaffEngine(load_db=True)
        except Exception as e:
            console.print(f"[red]引擎启动失败: {e}[/red]")
            sys.exit(1)
        
        console.print(Panel(f"[bold cyan]Wagstaff 源码透视镜 v3.1[/bold cyan]\n模式: {self.engine.mode.upper()} | 解析核心: Multi-Parser", border_style="blue"))
        if self.engine.tuning:
            console.print(f"[dim]⚡ Tuning 数值库就绪 ({len(self.engine.tuning.raw_map)} 条目)[/dim]")

    def get_structure_tree(self):
        """展示源码目录结构"""
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
        """文件名搜索"""
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
        """核心分析逻辑：根据 analyzer 返回的类型进行多态渲染"""
        from analyzer import LuaAnalyzer
        
        try:
            # 1. 统一入口解析 (Facade)
            data = LuaAnalyzer(content).get_report()
        except Exception as e:
            console.print(f"[red]解析失败: {e}[/red]")
            return
        
        # 2. 根据数据类型分发渲染
        dtype = data.get("type", "prefab")
        tree = Tree(f"🧬 [bold green]深度解析: {dtype.upper()}[/bold green]")
        
        if dtype == "loot":
            self._render_loot(tree, data)
        elif dtype == "widget":
            self._render_widget(tree, data)
        elif dtype == "strings":
            self._render_strings(tree, data)
        else:
            self._render_prefab(tree, data)

        console.print(Panel(tree, border_style="green"))
        input("按回车返回...")

    # === 子渲染器 (Renderers) ===

    def _render_loot(self, tree, data):
        """渲染掉落表数据"""
        if data.get('table_name'):
            tree.add(f"📜 表名: [bold gold1]{data['table_name']}[/bold gold1]")
        
        entries = data.get('entries', [])
        if entries:
            branch = tree.add(f"💰 掉落项 ({len(entries)})")
            for item in entries:
                if item.get('method') == 'Random':
                    branch.add(f"[cyan]{item['item']}[/cyan]: 权重 [yellow]{item['weight']}[/yellow]")
                else:
                    chance = item.get('chance', 0)
                    branch.add(f"[cyan]{item['item']}[/cyan]: 几率 [magenta]{chance}[/magenta]")

    def _render_widget(self, tree, data):
        """渲染 UI Widget 数据"""
        if data.get('classes'):
            c_branch = tree.add("🧩 UI 类定义")
            for c in data['classes']:
                c_branch.add(f"[bold white]{c['name']}[/bold white] (extends [dim]{c['parent']}[/dim])")
        
        if data.get('dependencies'):
            d_branch = tree.add("🔗 依赖模块")
            for d in data['dependencies']:
                d_branch.add(f"[dim]{d}[/dim]")

    def _render_strings(self, tree, data):
        """渲染文本配置数据"""
        if data.get('includes'):
            tree.add(f"📥 引入文件: {', '.join(data['includes'])}")
        
        if data.get('roots'):
            r_branch = tree.add("🔤 文本根节点 (Roots)")
            for root in data['roots']:
                r_branch.add(f"STRINGS.[bold yellow]{root}[/bold yellow]")

    def _render_prefab(self, tree, data):
        """渲染实体 Prefab 数据 (包含 Tuning 增强)"""
        # 1. 资源
        if data.get('assets'):
            asset_branch = tree.add(f"📦 资源引用 ({len(data['assets'])})")
            for a in data['assets']:
                style = "magenta" if "Anim" in a['type'] else "blue"
                asset_branch.add(f"[{style}]{a['type']}[/{style}]: {a['path']}")

        # 2. 逻辑 (Brain/SG/Tags)
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
                        # 使用 Engine 传入的 Tuning 进行增强
                        p_text = self.engine.tuning.enrich(p) if self.engine.tuning else p
                        target.add(f"[cyan]{p_text}[/cyan]")
                
                # 方法
                if comp['methods']:
                    target = node if len(comp['methods']) <=3 else node.add("[dim]函数调用[/dim]")
                    for m in comp['methods']:
                        # 使用 Engine 传入的 Tuning 进行增强
                        m_text = self.engine.tuning.enrich(m) if self.engine.tuning else m
                        target.add(f"[green]ƒ[/green] {m_text}")
        else:
            tree.add("[dim]⚙️ 功能组件 (无)[/dim]")

    def preview_file(self):
        """文件预览入口"""
        target = Prompt.ask("[bold green]👀 文件名[/bold green]")
        path = self.engine.find_file(target, fuzzy=True)
        if not path:
            console.print("[red]未找到[/red]")
            return
        
        console.print(f"[yellow]打开: {path}[/yellow]")
        content = self.engine.read_file(path)
        
        if content:
            # 只显示前 50 行以供概览
            syntax = Syntax("\n".join(content.splitlines()[:50]), "lua", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"{path} (Top 50 lines)", border_style="blue"))
            
            action = Prompt.ask("[bold cyan]操作[/bold cyan]", choices=["q", "a"], default="q")
            if action == "a":
                self.analyze_content(path, content)

    def show_tuning(self):
        """展示 Tuning 样本"""
        if not self.engine.tuning: 
            return console.print("[red]Tuning 未加载[/red]")
        
        console.print("[bold magenta]🔢 Tuning 数值采样[/bold magenta]")
        count = 0
        for k, v in list(self.engine.tuning.raw_map.items())[:10]:
             console.print(f"  [cyan]{k}[/cyan] = {v}")
             count += 1

def main():
    explorer = DSTExplorer()
    while True:
        console.print("\n[bold white on blue] 🦁 Wagstaff 探索面板 v3.1 [/bold white on blue]")
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