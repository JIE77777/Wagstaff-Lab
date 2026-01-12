#!/usr/bin/env python3
import os
import json
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

console = Console()
STATUS_FILE = "PROJECT_STATUS.json"

class ProjectManager:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"objective": "Unset", "tasks": [], "logs": [], "guidelines": []}

    def _save(self):
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def set_objective(self, obj):
        self.data["objective"] = obj
        self._save()
        console.print(f"[green]✅ 目标更新:[/green] {obj}")

    def add_task(self, task):
        self.data["tasks"].append({"desc": task, "status": "todo", "time": str(datetime.now())})
        self._save()
        console.print(f"[green]✅ 任务+1:[/green] {task}")
    
    def add_rule(self, rule):
        if "guidelines" not in self.data: self.data["guidelines"] = []
        self.data["guidelines"].append(rule)
        self._save()
        console.print(f"[bold magenta]📜 宗旨录入:[/bold magenta] {rule}")

    def complete_task(self, index):
        if 0 <= index < len(self.data["tasks"]):
            self.data["tasks"][index]["status"] = "done"
            self._save()
            console.print(f"[green]🎉 完成:[/green] {self.data['tasks'][index]['desc']}")
        else:
            console.print("[red]❌ 索引无效[/red]")

    def log_entry(self, msg):
        self.data["logs"].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}")
        if len(self.data["logs"]) > 10: self.data["logs"].pop(0)
        self._save()
        console.print("[green]📝 日志已记录[/green]")

    def show_status(self):
        console.clear()
        console.print(Panel(f"[bold blue]🎯 目标: {self.data.get('objective', 'Unset')}[/bold blue]"))
        
        t_table = Table(title="任务清单", box=None)
        t_table.add_column("ID", style="dim"); t_table.add_column("状态"); t_table.add_column("内容")
        for i, t in enumerate(self.data["tasks"]):
            status = "✅" if t["status"] == "done" else "⬜"
            style = "dim strike" if t["status"] == "done" else "bold"
            t_table.add_row(str(i), status, f"[{style}]{t['desc']}[/{style}]")
        console.print(t_table)
        
        if self.data.get("logs"):
            console.print("\n[dim]📜 最近日志:[/dim]")
            for l in self.data["logs"][-3:]:
                console.print(f"  {l}")

    def interactive_mode(self):
        while True:
            self.show_status()
            console.print("\n[bold cyan]操作菜单:[/bold cyan]")
            console.print("1. [green]✅ 完成任务[/]  2. [blue]➕ 新增任务[/]  3. [magenta]📝 写日志[/]  4. [yellow]🎯 改目标[/]  0. [red]退出[/]")
            
            choice = Prompt.ask("选择操作", choices=["0", "1", "2", "3", "4"], default="0")
            
            if choice == "0": break
            elif choice == "1":
                idx = IntPrompt.ask("输入任务ID")
                self.complete_task(idx)
            elif choice == "2":
                desc = Prompt.ask("输入任务描述")
                self.add_task(desc)
            elif choice == "3":
                log = Prompt.ask("输入日志内容")
                self.log_entry(log)
            elif choice == "4":
                obj = Prompt.ask("输入新目标")
                self.set_objective(obj)
            
            if choice != "0":
                input("\n按回车继续...")

def main():
    pm = ProjectManager()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        content = " ".join(sys.argv[2:])
        if cmd == "obj": pm.set_objective(content)
        elif cmd == "add": pm.add_task(content)
        elif cmd == "rule": pm.add_rule(content)
        elif cmd == "done": pm.complete_task(int(sys.argv[2]))
        elif cmd == "log": pm.log_entry(content)
        elif cmd == "ui": pm.interactive_mode() # 新增入口
        else: pm.show_status()
    else:
        # 默认直接进入交互模式，更省事
        pm.interactive_mode()

if __name__ == "__main__":
    main()
