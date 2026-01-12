#!/usr/bin/env python3
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from engine import WagstaffEngine # 直接调用引擎

console = Console()

def main():
    if len(sys.argv) < 2:
        console.print("[yellow]用法: python src/wiki.py <物品代码>[/yellow]")
        return
    
    target = sys.argv[1].lower()
    
    # 1. 启动引擎
    try:
        engine = WagstaffEngine()
    except Exception as e:
        console.print(f"[red]引擎启动失败: {e}[/red]")
        return

    # 2. 查配方
    real_name, recipe_data = engine.recipes.get(target)
    if not real_name: real_name = target
    
    # 3. 查数据 (使用引擎封装好的方法)
    prefab_data = engine.analyze_prefab(real_name)

    if not recipe_data and not prefab_data:
        console.print(f"[red]❌ 未找到 '{target}'[/red]")
        return

    # === 渲染层 (保持原有美观逻辑) ===
    console.print(Panel(f"[bold white on blue] 📚 Wagstaff 档案: {real_name.upper()} [/bold white on blue]"))
    
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=2)

    # 左：配方
    left_rows = []
    if recipe_data:
        t_name = recipe_data['tab'].replace("RECIPETABS.", "")
        rt = Table(title=f"📜 合成 ({t_name})", border_style="green", box=box.SIMPLE)
        rt.add_column("材料", style="cyan"); rt.add_column("数量", style="magenta")
        for ing in recipe_data['ingredients']:
            rt.add_row(ing['item'], engine.tuning.enrich(ing['amount']))
        left_rows.append(rt)
        if recipe_data.get('tech'): 
            left_rows.append(f"\n[dim]🔬 {recipe_data['tech'].replace('TECH.', '')}[/dim]")
    else:
        left_rows.append(Panel("[dim]不可合成[/dim]", border_style="dim"))

    # 右：组件
    right_rows = []
    if prefab_data:
        # Helpers
        if prefab_data.get('helpers'):
            tags = [f"[reverse cyan]{h.replace('Make','').replace('Inventory','')}[/reverse cyan]" for h in prefab_data['helpers']]
            right_rows.append(Text.from_markup(" ".join(tags) + "\n"))
        
        # Stats
        INTERESTING = ["weapon", "armor", "finiteuses", "edible", "tool", "fuel", "instrument"]
        st = Table(box=box.MINIMAL, show_header=False)
        st.add_column("C", style="dim"); st.add_column("V", style="white")
        
        has_stat = False
        for comp in prefab_data.get('components', []):
            if comp['name'] in INTERESTING:
                # 提取方法调用作为关键数据
                for m in comp['methods']:
                    if any(k in m for k in ["SetDamage", "SetAbsorption", "SetMaxUses", "GetHealth"]):
                        icon = "⚔️" if comp['name']=="weapon" else "⚙️"
                        st.add_row(f"{icon} {comp['name']}", m.split('(', 1)[1][:-1]) # 简略显示参数
                        has_stat = True
                # 提取属性
                for p in comp['properties']:
                    if "fuelvalue" in p or "armor" in p:
                         st.add_row(f"⚙️ {comp['name']}", p)
                         has_stat = True
        
        if has_stat: right_rows.append(st)
        else: right_rows.append("[dim]无核心战斗/生存数据[/dim]")
    else:
        right_rows.append("[red]⚠️ 无法读取文件[/red]")

    from rich.console import Group
    grid.add_row(Group(*left_rows), Group(*right_rows))
    console.print(grid)

if __name__ == "__main__":
    main()