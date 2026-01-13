#!/usr/bin/env python3
import sys
import re
import os
import math
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.prompt import Prompt

# 挂载 src 目录以导入核心模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from engine import WagstaffEngine
from analyzer import LuaAnalyzer, LootParser

console = Console()

class WagstaffWiki:
    def __init__(self):
        try:
            self.engine = WagstaffEngine(load_db=True)
        except Exception as e:
            console.print(f"[red]引擎初始化失败: {e}[/red]")
            sys.exit(1)

    def run(self, args):
        if not args:
            self._print_help()
            return

        command = args[0].lower()
        query = args[1] if len(args) > 1 else None

        if command == "recipe":
            self._search_recipe(query)
        elif command == "mob" or command == "item":
            self._analyze_prefab(query)
        elif command == "loot":
            self._find_loot_table(query)
        elif command == "find":
            # Find 现在进入交互模式，不需要手动输页码
            self._global_search_interactive(query)
        else:
            self._print_help()

    def _print_help(self):
        console.print(Panel("""
[bold cyan]📖 Wagstaff Wiki v2.3 (Interactive)[/bold cyan]

[green]bin/wagstaff wiki recipe <物品名>[/green]   查询配方
[green]bin/wagstaff wiki mob <生物名>[/green]      查询生物/物品详情
[green]bin/wagstaff wiki loot <表名>[/green]       查询掉落表
[green]bin/wagstaff wiki find <关键词>[/green]     [bold yellow]🔥 交互式代码搜索 (内置翻页)[/bold yellow]
""", title="Help", border_style="blue"))

    def _search_recipe(self, query):
        if not query: return console.print("[red]请输入物品名称[/red]")
        
        real_name, recipe_data = self.engine.recipes.get(query)
        
        if not recipe_data:
            candidates = [k for k in self.engine.recipes.recipes.keys() if query in k]
            if not candidates:
                return console.print(f"[red]未找到配方: {query}[/red]")
            if len(candidates) > 1:
                console.print(f"[yellow]可能的匹配: {', '.join(candidates[:5])}...[/yellow]")
                return
            real_name, recipe_data = self.engine.recipes.get(candidates[0])

        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column(justify="right")
        
        tab_info = recipe_data.get('tab', 'UNKNOWN').replace("RECIPETABS.", "")
        grid.add_row(f"[bold gold1]{real_name.upper()}[/bold gold1]", f"[dim]{tab_info}[/dim]")
        
        tech = recipe_data.get('tech', 'UNKNOWN').replace("TECH.", "")
        grid.add_row(f"[bold]科技:[/bold] {tech}", "")
        
        grid.add_row("\n[bold]所需材料:[/bold]")
        for ing in recipe_data.get('ingredients', []):
            grid.add_row(f"  • [cyan]{ing['item']}[/cyan]", f"[yellow]x{ing['amount']}[/yellow]")
            
        console.print(Panel(grid, title="🛠️  配方详情", border_style="gold1"))

    def _analyze_prefab(self, query):
        if not query: return console.print("[red]请输入名称[/red]")
        
        filepath = self.engine.find_file(query, fuzzy=True)
        if not filepath:
            return console.print(f"[red]未找到文件: {query}[/red]")

        content = self.engine.read_file(filepath)
        report = LuaAnalyzer(content).get_report()
        
        tree = Tree(f"🧬 [bold green]实体情报: {os.path.basename(filepath)}[/bold green]")
        tuning = self.engine.tuning

        if report.get('components'):
            comp_branch = tree.add("⚙️ 关键组件")
            for comp in report['components']:
                c_name = comp['name']
                has_content = comp.get('properties') or comp.get('methods')
                
                style = "bold yellow"
                if c_name in ['weapon', 'health', 'hunger', 'sanity', 'armor', 'lootdropper']:
                    style = "bold magenta"
                
                node_text = f"[{style}]{c_name}[/{style}]"
                
                if not has_content:
                    comp_branch.add(node_text)
                    continue
                
                comp_node = comp_branch.add(node_text)
                
                for prop in comp.get('properties', []):
                    val_text = tuning.enrich(prop) if tuning else prop
                    comp_node.add(f"[dim]•[/dim] {val_text}")

                for method in comp.get('methods', []):
                    val_text = tuning.enrich(method) if tuning else method
                    if any(k in method for k in ["SetDamage", "SetMaxHealth", "SetArmor"]):
                        comp_node.add(f"[bold green]ƒ {val_text}[/bold green]")
                    elif "SetChanceLootTable" in method or "SetSharedLootTable" in method:
                        comp_node.add(f"[bold red]ƒ {val_text}[/bold red]")
                    else:
                        comp_node.add(f"[dim]ƒ[/dim] {val_text}")

        console.print(Panel(tree, border_style="green"))
        console.print(f"\n💡 提示: 若发现 [red]SetChanceLootTable('NAME')[/red]，\n请运行: [bold cyan]bin/wagstaff wiki loot NAME[/bold cyan] 查看掉落率")

    def _find_loot_table(self, query):
        if not query: return console.print("[red]请输入掉落表名称 (例如: krampus)[/red]")
        
        console.print(f"[dim]正在全库搜索掉落表: '{query}' ...[/dim]")
        pattern = re.compile(r'SetSharedLootTable\s*\(\s*[\'"]' + re.escape(query) + r'[\'"]')
        
        found = False
        for filepath in self.engine.file_list:
            if not filepath.endswith(".lua"): continue
            content = self.engine.read_file(filepath)
            if not content: continue
            
            if pattern.search(content):
                self._render_loot_table(filepath, query, content)
                found = True
                break 
        
        if not found:
            console.print(f"[red]未找到掉落表定义: '{query}'[/red]")

    def _render_loot_table(self, filepath, table_name, content):
        console.print(f"[bold green]✅ 找到定义文件: {filepath}[/bold green]")
        parser = LootParser(content)
        data = parser.parse()
        
        if not data['entries']:
            console.print("[yellow]解析器未能提取到具体物品项。[/yellow]")
            return

        table = Table(title=f"💰 掉落表: {table_name}", box=None)
        table.add_column("物品 (Prefab)", style="cyan")
        table.add_column("几率 / 权重", style="magenta")
        table.add_column("类型", style="dim")

        for entry in data['entries']:
            val_str = ""
            if 'chance' in entry:
                pct = entry['chance'] * 100
                val_str = f"{pct:.2f}%" if pct < 1 else f"{pct:.0f}%"
            elif 'weight' in entry:
                val_str = f"权重 {entry['weight']}"
            
            table.add_row(entry['item'], val_str, entry['method'])

        console.print(Panel(table, border_style="gold1"))

    def _global_search_interactive(self, query):
        """交互式全局搜索 (TUI Mode)"""
        if not query: return console.print("[red]请输入搜索关键词[/red]")
        
        console.print(f"[bold cyan]🔍 正在扫描全库: '{query}' ...[/bold cyan]")
        
        # 1. 预先收集所有匹配 (只做一次)
        matches = []
        for f in self.engine.file_list:
            content = self.engine.read_file(f)
            if content and query in content:
                matches.append(f)
        
        total_count = len(matches)
        if total_count == 0:
            return console.print("[yellow]❌ 无结果[/yellow]")

        # 2. 进入交互循环
        page = 1
        per_page = 15
        total_pages = math.ceil(total_count / per_page)
        
        while True:
            # 清屏 (保持界面整洁)
            console.clear()
            
            # 计算切片
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            current_batch = matches[start_idx:end_idx]
            
            # 渲染表头
            console.print(Panel(f"🔍 关键词: [bold green]{query}[/bold green] | 命中: {total_count} 文件", style="blue"))
            
            # 渲染列表
            table = Table(box=None, show_header=True, header_style="bold dim")
            table.add_column("No.", justify="right", style="dim", width=4)
            table.add_column("文件路径", style="cyan")
            
            for i, f in enumerate(current_batch):
                idx = start_idx + i + 1
                # 简单高亮文件名
                dir_path, fname = os.path.split(f)
                display_path = f"{dir_path}/[bold white]{fname}[/bold white]"
                table.add_row(str(idx), display_path)
                
            console.print(table)
            
            # 底部状态栏
            status_color = "green" if page == total_pages else "yellow"
            console.print(f"\n[dim]📄 页码: [{status_color}]{page}/{total_pages}[/{status_color}][/dim]")
            
            # 构建提示
            options = []
            if page < total_pages: options.append("[n]下一页")
            if page > 1: options.append("[p]上一页")
            options.append("[q]退出")
            
            prompt_text = " ".join(options)
            
            # 获取输入
            action = Prompt.ask(f"[bold]{prompt_text}[/bold]", choices=["n", "p", "q"], show_choices=False)
            
            if action == 'q':
                console.print("[dim]搜索会话结束[/dim]")
                break
            elif action == 'n':
                if page < total_pages: page += 1
            elif action == 'p':
                if page > 1: page -= 1

if __name__ == "__main__":
    WagstaffWiki().run(sys.argv[1:])