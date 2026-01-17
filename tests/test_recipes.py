#!/usr/bin/env python3
import sys
import time
from rich.console import Console
from rich.table import Table
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine

console = Console()

def main():
    console.print("[bold blue]🧪 配方解析器验收测试 (基于 Wagstaff Engine)[/bold blue]")
    
    # 1. 启动引擎
    try:
        start_t = time.time()
        engine = WagstaffEngine(load_db=True)
        duration = (time.time() - start_t) * 1000
    except Exception as e:
        console.print(f"[red]引擎启动失败: {e}[/red]")
        return
    
    # 2. 统计
    count = len(engine.recipes.recipes)
    count_style = "green" if count > 500 else "red"
    
    console.print(f"加载耗时: [bold]{duration:.2f} ms[/bold]")
    console.print(f"发现配方: [{count_style}]{count}[/{count_style}]")

    # 3. 抽查
    check_list = ["spear", "armorwood", "hambat", "firestaff"]
    table = Table(title="关键物品验证", border_style="blue")
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="dim")
    table.add_column("Ingredients", style="white")
    
    for item in check_list:
        real_name, data = engine.recipes.get(item)
        if data:
            ing_str = ", ".join([f"{i['item']}x{i['amount']}" for i in data['ingredients']])
            table.add_row(item, real_name, ing_str)
        else:
            table.add_row(item, "-", "[red]Not Found[/red]")
        
    console.print(table)

if __name__ == "__main__":
    main()
