#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

# 使用 Path 处理路径，确保在任何目录执行都能找到文件
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "PROJECT_STATUS.json"

console = Console()

class ProjectManager:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if not DATA_FILE.exists():
            self._init_empty()
        else:
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                self.data = self._migrate_schema(raw_data)
                # 加载后立即保存一次，完成格式固化
                self.save() 
            except json.JSONDecodeError:
                console.print("[red]JSON 文件损坏，已重置[/red]")
                self._init_empty()

    def _init_empty(self):
        self.data = {
            "OBJECTIVE": "Unset",
            "TASKS_TODO": [],
            "TASKS_DONE": [],
            "TASKS_PENDING": [], # 预留
            "RECENT_LOGS": [],
            "DEV_MANIFESTO": []
        }
        self.save()

    def _migrate_schema(self, old_data):
        """
        自动迁移逻辑：将 v1 (tasks list) 数据转换为 v2 (TODO/DONE lists)
        """
        new_data = {
            "OBJECTIVE": old_data.get("OBJECTIVE") or old_data.get("objective", "Unset"),
            "TASKS_TODO": old_data.get("TASKS_TODO", []),
            "TASKS_DONE": old_data.get("TASKS_DONE", []),
            "RECENT_LOGS": old_data.get("RECENT_LOGS") or old_data.get("logs", []),
            "DEV_MANIFESTO": old_data.get("DEV_MANIFESTO") or old_data.get("guidelines", [])
        }

        # 处理旧版 "tasks" 列表迁移
        if "tasks" in old_data and isinstance(old_data["tasks"], list):
            console.print("[yellow]⚡ 检测到旧版数据结构，正在执行自动迁移...[/yellow]")
            for t in old_data["tasks"]:
                # 旧版结构: {"desc": "...", "status": "done/todo"}
                if isinstance(t, dict):
                    desc = t.get("desc", "")
                    status = t.get("status", "todo")
                    if status == "done":
                        new_data["TASKS_DONE"].append(desc)
                    else:
                        new_data["TASKS_TODO"].append(desc)
                # 兼容已经是字符串的情况
                elif isinstance(t, str):
                    new_data["TASKS_TODO"].append(t)

        return new_data

    def save(self):
        # 原子写入防止损坏
        tmp_file = DATA_FILE.with_name(DATA_FILE.name + ".tmp")
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        tmp_file.replace(DATA_FILE)

    def show_status(self):
        console.clear()
        # 1. 目标
        obj_text = self.data.get("OBJECTIVE", "Unset")
        console.print(Panel(f"[bold cyan]🎯 目标: {obj_text}[/bold cyan]", border_style="blue"))
        
        # 2. 待办任务
        todo_list = self.data["TASKS_TODO"]
        table = Table(title=f"📝 待办任务 ({len(todo_list)})", box=None, show_header=True)
        table.add_column("ID", style="dim", width=4)
        table.add_column("内容", style="yellow")
        
        if not todo_list:
            table.add_row("-", "[dim]暂无待办[/dim]")
        else:
            for i, task in enumerate(todo_list):
                table.add_row(str(i + 1), task)
        console.print(table)

        # 3. 已完成 (显示最近 5 条)
        done_list = self.data["TASKS_DONE"]
        if done_list:
            console.print(f"\n[dim]✅ 最近完成 ({len(done_list)}):[/dim]")
            for task in done_list[-5:]:
                console.print(f"  [green]✔ {task}[/green]")

        # 4. 日志 (显示最近 5 条)
        logs = self.data["RECENT_LOGS"]
        if logs:
            console.print("\n[dim]📜 最近日志:[/dim]")
            for log in logs[-5:]:
                console.print(f"  [dim]{log}[/dim]")
        
        console.print("\n[dim]指令: add <任务> | done <ID> | log <内容> | obj <目标> | q (退出)[/dim]")

    def run_command(self, cmd_str):
        if not cmd_str: return
        parts = cmd_str.split(" ", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "add":
            if not arg: return console.print("[red]任务内容不能为空[/red]")
            self.data["TASKS_TODO"].append(arg)
            console.print(f"[green]已添加任务: {arg}[/green]")
            self.save()
        elif cmd == "done":
            try:
                idx = int(arg) - 1
                if 0 <= idx < len(self.data["TASKS_TODO"]):
                    task = self.data["TASKS_TODO"].pop(idx)
                    self.data["TASKS_DONE"].append(task)
                    console.print(f"[green]完成任务: {task}[/green]")
                    self.save()
                else:
                    console.print("[red]ID 无效[/red]")
            except ValueError:
                console.print("[red]请输入数字 ID[/red]")
        elif cmd == "log":
            if not arg: return
            ts = datetime.now().strftime("[%Y-%m-%d %H:%M]")
            self.data["RECENT_LOGS"].append(f"{ts} {arg}")
            console.print("[green]日志已记录[/green]")
            self.save()
        elif cmd == "obj":
            self.data["OBJECTIVE"] = arg
            console.print("[green]目标已更新[/green]")
            self.save()
        elif cmd in ["q", "quit", "exit"]:
            sys.exit(0)
        else:
            console.print("[red]未知指令[/red]")

    def interactive_mode(self):
        while True:
            self.show_status()
            try:
                cmd = Prompt.ask("pm")
                self.run_command(cmd)
            except KeyboardInterrupt:
                sys.exit(0)

    def cli_mode(self, args):
        cmd = args[0]
        # 处理 log 命令后面带空格的情况
        if cmd == "log" and len(args) > 1:
            val = " ".join(args[1:])
        elif len(args) > 1:
            val = args[1]
        else:
            val = ""
        
        self.run_command(f"{cmd} {val}")

def main():
    pm = ProjectManager()
    if len(sys.argv) > 1:
        pm.cli_mode(sys.argv[1:])
    else:
        pm.interactive_mode()

if __name__ == "__main__":
    main()