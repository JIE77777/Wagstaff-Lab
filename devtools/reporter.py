#!/usr/bin/env python3
import os
import sys
import re
from collections import Counter, defaultdict
from rich.console import Console
from rich.progress import track

# 挂载 core 并引入引擎
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.engine import WagstaffEngine

console = Console()

# === [修复] 动态定位项目路径 ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
REPORT_DIR = os.path.join(PROJECT_ROOT, "data", "reports")

class WagstaffReporter:
    def __init__(self):
        # 启动引擎，不需要加载数据库(我们只做正则扫描)
        self.engine = WagstaffEngine(load_db=False, silent=True)
        self._ensure_report_dir()

    def _ensure_report_dir(self):
        if not os.path.exists(REPORT_DIR):
            os.makedirs(REPORT_DIR)
            console.print(f"[green]📁 创建报告目录: {REPORT_DIR}[/green]")

    def generate_asset_report(self):
        """扫描全服资产分布"""
        console.print("[bold blue]📡 正在生成资产分布报告...[/bold blue]")
        
        TARGETS = {
            "STRINGS": re.compile(r'STRINGS\.[A-Z0-9_]+\s*='),
            "Prefabs": re.compile(r'\bPrefab\s*\('),
            "LootTables": re.compile(r'\bSetLoot\s*\(|\bSetChanceLoot\s*\('),
            "Brains": re.compile(r'require\s*[\("\']brains/'),
            "Widgets": re.compile(r'require\s*[\("\']widgets/'),
        }
        
        stats = defaultdict(Counter)
        lua_files = [f for f in self.engine.file_list if f.endswith(".lua")]
        
        for fname in track(lua_files, description="Scanning Assets..."):
            content = self.engine.read_file(fname)
            if not content: continue
            clean = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
            
            for cat, pattern in TARGETS.items():
                matches = pattern.findall(clean)
                if matches:
                    stats[cat][fname] += len(matches)

        out_path = os.path.join(REPORT_DIR, "asset_registry.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write("# Wagstaff Asset Registry\n\n")
            f.write("| Category | Total Definitions | Top File |\n")
            f.write("|----------|-------------------|----------|\n")
            for cat, file_counts in stats.items():
                total = sum(file_counts.values())
                top_file = file_counts.most_common(1)[0][0]
                f.write(f"| {cat} | {total} | `{top_file}` |\n")
            
            f.write("\n## Detailed Breakdown\n")
            for cat, file_counts in stats.items():
                f.write(f"\n### {cat}\n")
                for fname, count in file_counts.most_common(10):
                    f.write(f"- `{fname}`: {count}\n")
        console.print(f"[green]✅ 报告已保存: {out_path}[/green]")

    def generate_recipe_report(self):
        """扫描配方分布"""
        console.print("[bold blue]🍳 正在生成配方分布报告...[/bold blue]")
        
        pattern = re.compile(r'^\s*([a-zA-Z0-9_]*Recipe[a-zA-Z0-9_]*)\s*\(', re.MULTILINE)
        stats = Counter()
        file_stats = defaultdict(int)
        
        lua_files = [f for f in self.engine.file_list if f.endswith(".lua")]
        
        for fname in track(lua_files, description="Scanning Recipes..."):
            content = self.engine.read_file(fname)
            if not content: continue
            clean = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
            
            matches = pattern.findall(clean)
            for m in matches:
                if "Get" in m or "Find" in m: continue
                stats[m] += 1
                file_stats[fname] += 1

        out_path = os.path.join(REPORT_DIR, "recipe_distribution.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write("# Wagstaff Recipe Distribution\n\n")
            f.write("## Function Usage\n")
            for func, count in stats.most_common():
                f.write(f"- **{func}**: {count}\n")
            f.write("\n## File Hotspots (Top 20)\n")
            for fname, count in sorted(file_stats.items(), key=lambda x:x[1], reverse=True)[:20]:
                f.write(f"- `{fname}`: {count} recipes\n")

        console.print(f"[green]✅ 报告已保存: {out_path}[/green]")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reporter.py [assets|recipes|all]")
        sys.exit(1)
    reporter = WagstaffReporter()
    cmd = sys.argv[1]
    if cmd == "assets" or cmd == "all": reporter.generate_asset_report()
    if cmd == "recipes" or cmd == "all": reporter.generate_recipe_report()
