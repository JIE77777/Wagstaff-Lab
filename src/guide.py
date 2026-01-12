#!/usr/bin/env python3
import os
import sys
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path

# 引入配置和注册表
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from registry import get_tools

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_status():
    status_path = PROJECT_ROOT / "PROJECT_STATUS.json"
    if status_path.exists():
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    data = load_status()
    
    console.print(Panel("[bold white on blue] 🧪 Wagstaff-Lab (v2.2) 控制台 [/bold white on blue]", border_style="blue"))
    
    if "objective" in data:
        console.print(f"[bold green]🎯 当前目标:[/bold green] {data['objective']}")
    
    # 增加 Usage 列的展示
    console.print("\n[bold yellow]🛠️  工具箱使用指南[/bold yellow]")
    table = Table(box=None, show_header=True, header_style="bold cyan")
    table.add_column("工具", style="bold")
    table.add_column("描述")
    table.add_column("标准用法 (Usage)", style="green")
    
    for tool in get_tools():
        table.add_row(
            tool['file'], 
            tool['desc'], 
            tool.get('usage', 'N/A')
        )

    console.print(table)
    console.print("\n[dim]💡 输入 [bold]pm ui[/bold] 管理任务，输入 [bold]wagstaff snap[/bold] 更新快照。[/dim]")

if __name__ == "__main__":
    main()
