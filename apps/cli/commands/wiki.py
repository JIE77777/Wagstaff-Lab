#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apps/cli/commands/wiki.py

CLI-oriented "wiki" front-end.

Notes
- This module is intentionally a thin UI layer.
- Core parsing/indexing lives in `engine.py`, `craft_recipes.py`, `analyzer.py`, etc.
"""

import math
import os
import re
import sys
from pathlib import Path
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.tree import Tree

from apps.cli.cli_common import PROJECT_ROOT
from core.engine import WagstaffEngine  # noqa: E402
from core.parsers import LuaAnalyzer, LootParser  # noqa: E402

console = Console()


def _parse_inventory_spec(spec: str) -> Dict[str, float]:
    """Parse inventory spec into {item: count}.

    Accepted examples
    - "twigs=2,flint=1"
    - "twigs:2 flint:1"
    - "twigs flint" (defaults to 1)

    Non-numeric counts are ignored.
    """
    out: Dict[str, float] = {}
    if not spec:
        return out

    s = spec.strip()
    if not s:
        return out

    # Fast path: key=value / key:value pairs
    pairs = re.findall(r"([A-Za-z0-9_]+)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", s)
    for k, v in pairs:
        try:
            out[k] = out.get(k, 0.0) + float(v)
        except Exception:
            pass

    if out:
        return out

    # Fallback: plain tokens => count=1
    tokens = re.split(r"[\s,]+", s)
    for t in tokens:
        t = (t or "").strip()
        if not t:
            continue
        out[t] = out.get(t, 0.0) + 1.0
    return out


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

        if command == "recipe":
            # Supported:
            #   wiki recipe <name>
            #   wiki recipe tab <TAB>
            #   wiki recipe filter <FILTER>
            #   wiki recipe who <BUILDER_TAG>
            #   wiki recipe tech <TECH>
            #   wiki recipe uses <ITEM>
            #   wiki recipe can <INV_SPEC>
            #   wiki recipe missing <RECIPE> <INV_SPEC>
            if len(args) >= 2 and args[1].lower() in ("tab", "filter", "who", "tech", "uses", "can", "missing", "tabs", "filters"):
                sub = args[1].lower()

                if sub == "tabs":
                    self._list_recipe_tabs()
                elif sub == "filters":
                    self._list_recipe_filters()
                elif sub == "missing":
                    if len(args) < 4:
                        return console.print("[red]用法: wiki recipe missing <recipe> <inv>[/red]")
                    recipe = args[2]
                    inv = _parse_inventory_spec(" ".join(args[3:]))
                    self._recipe_missing(recipe, inv)
                else:
                    if len(args) < 3:
                        return console.print("[red]缺少参数[/red]")
                    q = " ".join(args[2:])
                    if sub == "tab":
                        self._list_recipe_by_tab(q)
                    elif sub == "filter":
                        self._list_recipe_by_filter(q)
                    elif sub == "who":
                        self._list_recipe_by_builder_tag(q)
                    elif sub == "tech":
                        self._list_recipe_by_tech(q)
                    elif sub == "uses":
                        self._list_recipe_by_ingredient(q)
                    elif sub == "can":
                        inv = _parse_inventory_spec(q)
                        self._list_recipe_craftable(inv)
            else:
                q = args[1] if len(args) > 1 else None
                self._search_recipe(q)

        elif command in ("mob", "item"):
            q = args[1] if len(args) > 1 else None
            self._analyze_prefab(q)

        elif command == "loot":
            q = args[1] if len(args) > 1 else None
            self._find_loot_table(q)

        elif command == "food":
            # Minimal preparedfoods index
            #   wiki food <name>
            #   wiki food can <INV_SPEC>
            if len(args) >= 2 and args[1].lower() == "can":
                inv = _parse_inventory_spec(" ".join(args[2:]))
                self._list_food_cookable(inv)
            else:
                q = args[1] if len(args) > 1 else None
                self._show_food(q)

        elif command == "find":
            q = args[1] if len(args) > 1 else None
            self._global_search_interactive(q)

        else:
            self._print_help()

    def _print_help(self):
        console.print(
            Panel(
                """
[bold cyan]📖 Wagstaff Wiki v2.6 (Craft + Cooking)[/bold cyan]

[green]wagstaff wiki recipe <配方名/产物名>[/green]
[green]wagstaff wiki recipe tab <TAB>[/green]            按制作栏大类列出
[green]wagstaff wiki recipe filter <FILTER>[/green]      按筛选分类列出
[green]wagstaff wiki recipe who <TAG>[/green]            按角色专属列出 (builder_tag)
[green]wagstaff wiki recipe tech <TECH>[/green]          按科技需求列出
[green]wagstaff wiki recipe uses <ITEM>[/green]          反查：哪些配方需要该材料
[green]wagstaff wiki recipe can <INV>[/green]            给定材料，列出可制作配方
[green]wagstaff wiki recipe missing <R> <INV>[/green]    给定材料，查看缺少哪些
[green]wagstaff wiki recipe tabs[/green]                 查看 TAB 顺序
[green]wagstaff wiki recipe filters[/green]              查看 FILTER 定义(含icon字段)

[green]wagstaff wiki food <食谱名>[/green]                查询烹饪食谱(准备食物)
[green]wagstaff wiki food can <INV>[/green]              近似：按 card_ingredients 判断可做食谱

[green]wagstaff wiki mob <生物名>[/green]                查询生物/物品详情
[green]wagstaff wiki loot <表名>[/green]                 查询掉落表
[green]wagstaff wiki find <关键词>[/green]               交互式代码搜索

INV 格式例：twigs=2,flint=1  或  twigs:2 flint:1
""",
                title="Help",
                border_style="blue",
            )
        )

    # ---------- recipe detail ----------

    def _search_recipe(self, query):
        if not query:
            return console.print("[red]请输入配方名称[/red]")

        real_name, recipe_data = self.engine.recipes.get(query)  # type: ignore[union-attr]

        if not recipe_data:
            # fallback: 子串匹配
            db = self.engine.recipes  # type: ignore[assignment]
            candidates = [k for k in db.recipes.keys() if query in k]
            if not candidates:
                return console.print(f"[red]未找到配方: {query}[/red]")
            if len(candidates) > 1:
                console.print(f"[yellow]可能的匹配: {', '.join(candidates[:8])}...[/yellow]")
                return
            real_name, recipe_data = self.engine.recipes.get(candidates[0])  # type: ignore[union-attr]

        tab = str(recipe_data.get("tab", "UNKNOWN"))
        tech = str(recipe_data.get("tech", "UNKNOWN"))

        filters = recipe_data.get("filters") or []
        builder_tags = recipe_data.get("builder_tags") or ([] if recipe_data.get("builder_tag") is None else [recipe_data.get("builder_tag")])
        product = recipe_data.get("product") or None

        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column(justify="right")

        grid.add_row(f"[bold gold1]{real_name.upper()}[/bold gold1]", f"[dim]{tab}[/dim]")
        grid.add_row(f"[bold]科技:[/bold] {tech}", "")

        if filters:
            grid.add_row(f"[bold]Filters:[/bold] {', '.join(filters)}", "")
        if builder_tags:
            grid.add_row(f"[bold]角色专属:[/bold] {', '.join([str(x) for x in builder_tags])}", "")
        if product:
            grid.add_row(f"[bold]产物:[/bold] {product}", "")

        grid.add_row("\n[bold]所需材料:[/bold]")
        for ing in recipe_data.get("ingredients", []):
            amt = ing.get("amount")
            grid.add_row(f"  • [cyan]{ing.get('item')}[/cyan]", f"[yellow]x{amt}[/yellow]")

        console.print(Panel(grid, title="🛠️  配方详情", border_style="gold1"))

    # ---------- recipe list ----------

    def _render_recipe_list(self, title: str, names):
        names = list(names or [])
        if not names:
            console.print(f"[yellow]无结果: {title}[/yellow]")
            return

        table = Table(title=f"{title} (共 {len(names)})", box=None, show_header=True, header_style="bold dim")
        table.add_column("No.", justify="right", style="dim", width=4)
        table.add_column("Recipe", style="cyan")
        table.add_column("Tab", style="dim")
        table.add_column("Tech", style="dim")

        # 只展示前 80 条，避免刷屏（后续可做交互分页）
        show = names[:80]
        for i, nm in enumerate(show, start=1):
            _, r = self.engine.recipes.get(nm)  # type: ignore[union-attr]
            tab = str((r or {}).get("tab", "UNKNOWN"))
            tech = str((r or {}).get("tech", "UNKNOWN"))
            table.add_row(str(i), nm, tab, tech)

        console.print(Panel(table, border_style="blue"))
        if len(names) > 80:
            console.print(f"[dim]... 其余 {len(names) - 80} 条未显示[/dim]")

    def _list_recipe_by_tab(self, tab):
        names = self.engine.recipes.list_by_tab(tab)  # type: ignore[union-attr]
        self._render_recipe_list(f"🧭 Tab = {tab}", names)

    def _list_recipe_by_filter(self, flt):
        names = self.engine.recipes.list_by_filter(flt)  # type: ignore[union-attr]
        self._render_recipe_list(f"🔎 Filter = {flt}", names)

    def _list_recipe_by_builder_tag(self, tag):
        names = self.engine.recipes.list_by_builder_tag(tag)  # type: ignore[union-attr]
        self._render_recipe_list(f"👤 builder_tag = {tag}", names)

    def _list_recipe_by_tech(self, tech):
        names = self.engine.recipes.list_by_tech(tech)  # type: ignore[union-attr]
        self._render_recipe_list(f"🧪 Tech = {tech}", names)

    def _list_recipe_tabs(self):
        db = self.engine.recipes  # type: ignore[assignment]
        if not db:
            return console.print("[red]recipes DB not loaded[/red]")

        rows = db.tab_order or sorted(db.by_tab.keys())
        table = Table(title=f"Craft Tabs ({len(rows)})", box=None, show_header=True, header_style="bold dim")
        table.add_column("No.", justify="right", style="dim", width=4)
        table.add_column("TAB", style="cyan")
        for i, t in enumerate(rows, start=1):
            table.add_row(str(i), str(t))
        console.print(Panel(table, border_style="blue"))

    def _list_recipe_filters(self):
        db = self.engine.recipes  # type: ignore[assignment]
        if not db:
            return console.print("[red]recipes DB not loaded[/red]")

        defs = db.filter_defs or []
        table = Table(title=f"Craft Filters ({len(defs)})", box=None, show_header=True, header_style="bold dim")
        table.add_column("No.", justify="right", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Image", style="dim")
        table.add_column("Atlas", style="dim")

        for i, d in enumerate(defs, start=1):
            table.add_row(str(i), str(d.get("name")), str(d.get("image")), str(d.get("atlas")))

        console.print(Panel(table, border_style="blue"))

    def _list_recipe_by_ingredient(self, item: str):
        db = self.engine.recipes  # type: ignore[assignment]
        if not db:
            return console.print("[red]recipes DB not loaded[/red]")
        names = db.list_by_ingredient(item)
        self._render_recipe_list(f"🧱 Uses ingredient = {item}", names)

    def _list_recipe_craftable(self, inv: Dict[str, float]):
        db = self.engine.recipes  # type: ignore[assignment]
        if not db:
            return console.print("[red]recipes DB not loaded[/red]")

        names = db.craftable(inv)
        self._render_recipe_list("✅ Craftable recipes", names)

    def _recipe_missing(self, recipe: str, inv: Dict[str, float]):
        db = self.engine.recipes  # type: ignore[assignment]
        if not db:
            return console.print("[red]recipes DB not loaded[/red]")

        missing = db.missing_for(recipe, inv)
        if not missing:
            return console.print("[green]✅ 材料充足（或配方不存在/无材料）[/green]")

        table = Table(title=f"Missing for: {recipe}", box=None, show_header=True, header_style="bold dim")
        table.add_column("Item", style="cyan")
        table.add_column("Need", justify="right")
        table.add_column("Have", justify="right", style="dim")

        for row in missing:
            table.add_row(row["item"], str(row["need"]), str(row["have"]))

        console.print(Panel(table, border_style="red"))

    # ---------- cooking recipes ----------

    def _show_food(self, query: str):
        if not query:
            return console.print("[red]请输入食谱名[/red]")

        db = self.engine.cooking_recipes or {}
        if query not in db:
            # fuzzy contains
            cands = [k for k in db.keys() if query in k]
            if not cands:
                return console.print(f"[red]未找到食谱: {query}[/red]")
            if len(cands) > 1:
                console.print(f"[yellow]可能的匹配: {', '.join(cands[:10])}...[/yellow]")
                return
            query = cands[0]

        r = db.get(query, {})

        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column(justify="right")

        grid.add_row(f"[bold gold1]{query.upper()}[/bold gold1]", str(r.get("foodtype", "")))

        for k in ("hunger", "health", "sanity", "perishtime", "cooktime", "priority", "weight"):
            if k in r:
                grid.add_row(f"[bold]{k}:[/bold] {r.get(k)}", "")

        tags = r.get("tags")
        if tags:
            grid.add_row(f"[bold]tags:[/bold] {tags}", "")

        card = r.get("card_ingredients") or []
        if card:
            grid.add_row("\n[bold]card_ingredients (近似用):[/bold]")
            for it, cnt in card:
                grid.add_row(f"  • [cyan]{it}[/cyan]", f"[yellow]x{cnt}[/yellow]")

        console.print(Panel(grid, title="🍲 食谱详情", border_style="gold1"))

    def _list_food_cookable(self, inv: Dict[str, float]):
        # NOTE: This is an approximation: uses card_ingredients as requirements.
        db = self.engine.cooking_recipes or {}
        if not db:
            return console.print("[yellow]未加载 cooking recipes[/yellow]")

        ok: List[str] = []
        for name, rec in db.items():
            req = rec.get("card_ingredients")
            if not req:
                continue
            good = True
            for it, cnt in req:
                try:
                    need = float(cnt)
                except Exception:
                    good = False
                    break
                have = float(inv.get(str(it), 0.0))
                if have + 1e-9 < need:
                    good = False
                    break
            if good:
                ok.append(name)

        ok = sorted(ok)
        table = Table(title=f"Cookable (approx) ({len(ok)})", box=None, show_header=True, header_style="bold dim")
        table.add_column("No.", justify="right", style="dim", width=4)
        table.add_column("Food", style="cyan")
        for i, nm in enumerate(ok[:120], start=1):
            table.add_row(str(i), nm)
        console.print(Panel(table, border_style="blue"))
        if len(ok) > 120:
            console.print(f"[dim]... 其余 {len(ok) - 120} 条未显示[/dim]")

    # ---------- prefab / loot / find (kept) ----------

    def _analyze_prefab(self, query):
        if not query:
            return console.print("[red]请输入名称[/red]")

        filepath = self.engine.find_file(query, fuzzy=True)
        if not filepath:
            return console.print(f"[red]未找到文件: {query}[/red]")

        content = self.engine.read_file(filepath)
        report = LuaAnalyzer(content).get_report()

        tree = Tree(f"🧬 [bold green]实体情报: {os.path.basename(filepath)}[/bold green]")
        tuning = self.engine.tuning

        if report.get("components"):
            comp_branch = tree.add("⚙️ 关键组件")
            for comp in report["components"]:
                c_name = comp["name"]
                has_content = comp.get("properties") or comp.get("methods")

                style = "bold yellow"
                if c_name in ["weapon", "health", "hunger", "sanity", "armor", "lootdropper"]:
                    style = "bold magenta"

                node_text = f"[{style}]{c_name}[/{style}]"

                if not has_content:
                    comp_branch.add(node_text)
                    continue

                comp_node = comp_branch.add(node_text)

                for prop in comp.get("properties", []):
                    val_text = tuning.enrich(prop) if tuning else prop
                    comp_node.add(f"[dim]•[/dim] {val_text}")

                for method in comp.get("methods", []):
                    val_text = tuning.enrich(method) if tuning else method
                    if any(k in method for k in ["SetDamage", "SetMaxHealth", "SetArmor"]):
                        comp_node.add(f"[bold green]ƒ {val_text}[/bold green]")
                    elif "SetChanceLootTable" in method or "SetSharedLootTable" in method:
                        comp_node.add(f"[bold red]ƒ {val_text}[/bold red]")
                    else:
                        comp_node.add(f"[dim]ƒ[/dim] {val_text}")

        console.print(Panel(tree, border_style="green"))
        console.print(
            "\n💡 提示: 若发现 [red]SetChanceLootTable('NAME')[/red]，\n"
            "请运行: [bold cyan]wagstaff wiki loot NAME[/bold cyan] 查看掉落率"
        )

    def _find_loot_table(self, query):
        if not query:
            return console.print("[red]请输入掉落表名称 (例如: krampus)[/red]")

        console.print(f"[dim]正在全库搜索掉落表: '{query}' ...[/dim]")
        pattern = re.compile(r"SetSharedLootTable\s*\(\s*[\'\"]" + re.escape(query) + r"[\'\"]")

        found = False
        for filepath in self.engine.file_list:
            if not filepath.endswith(".lua"):
                continue
            content = self.engine.read_file(filepath)
            if not content:
                continue

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

        if not data["entries"]:
            console.print("[yellow]解析器未能提取到具体物品项。[/yellow]")
            return

        table = Table(title=f"💰 掉落表: {table_name}", box=None)
        table.add_column("物品 (Prefab)", style="cyan")
        table.add_column("几率 / 权重", style="magenta")
        table.add_column("类型", style="dim")

        for entry in data["entries"]:
            val_str = ""
            if "chance" in entry:
                pct = entry["chance"] * 100
                val_str = f"{pct:.2f}%" if pct < 1 else f"{pct:.0f}%"
            elif "weight" in entry:
                val_str = f"权重 {entry['weight']}"

            table.add_row(entry["item"], val_str, entry["method"])

        console.print(Panel(table, border_style="gold1"))

    def _global_search_interactive(self, query):
        if not query:
            return console.print("[red]请输入搜索关键词[/red]")

        console.print(f"[bold cyan]🔍 正在扫描全库: '{query}' ...[/bold cyan]")

        matches = []
        for f in self.engine.file_list:
            content = self.engine.read_file(f)
            if content and query in content:
                matches.append(f)

        total_count = len(matches)
        if total_count == 0:
            return console.print("[yellow]❌ 无结果[/yellow]")

        page = 1
        per_page = 15
        total_pages = math.ceil(total_count / per_page)

        while True:
            console.clear()
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            current_batch = matches[start_idx:end_idx]

            console.print(Panel(f"🔍 关键词: [bold green]{query}[/bold green] | 命中: {total_count} 文件", style="blue"))

            table = Table(box=None, show_header=True, header_style="bold dim")
            table.add_column("No.", justify="right", style="dim", width=4)
            table.add_column("文件路径", style="cyan")

            for i, f in enumerate(current_batch):
                idx = start_idx + i + 1
                dir_path, fname = os.path.split(f)
                display_path = f"{dir_path}/[bold white]{fname}[/bold white]"
                table.add_row(str(idx), display_path)

            console.print(table)
            status_color = "green" if page == total_pages else "yellow"
            console.print(f"\n[dim]📄 页码: [{status_color}]{page}/{total_pages}[/{status_color}][/dim]")
            console.print("[dim]操作: n 下一页 | p 上一页 | q 退出[/dim]")

            cmd = input("\n> ").strip().lower()
            if cmd == "q":
                break
            elif cmd == "n" and page < total_pages:
                page += 1
            elif cmd == "p" and page > 1:
                page -= 1


def main(argv=None):
    argv = argv or sys.argv[1:]
    WagstaffWiki().run(argv)


if __name__ == "__main__":
    main()
