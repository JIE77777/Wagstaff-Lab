#!/usr/bin/env python3
import os
import re
import sys
import zipfile
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box

# === 引入 Wagstaff 工具库 ===
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import wagstaff_config

console = Console()

class DSTWiki:
    def __init__(self):
        # 1. 继承配置
        self.base_dir = wagstaff_config.get('PATHS', 'DST_ROOT')
        self.zip_path = os.path.join(self.base_dir, "data", "databundles", "scripts.zip")
        self.fallback_dir = os.path.join(self.base_dir, "data", "scripts")
        
        self.tuning_data = {}  # 存放数值常量
        self.source = None
        self.mode = None
        
        self.init_source()
        self.load_tuning_db() # 预加载数值库

    def init_source(self):
        """初始化数据源 (Zip 或 文件夹)"""
        if os.path.exists(self.zip_path):
            self.mode = 'zip'
            self.source = zipfile.ZipFile(self.zip_path, 'r')
        elif os.path.exists(self.fallback_dir):
            self.mode = 'folder'
            self.source = self.fallback_dir
        else:
            console.print(f"[red]❌ 致命错误: 无法定位 scripts 数据源[/red]")
            sys.exit(1)

    def read_file(self, internal_path):
        """读取文件内容的通用适配器"""
        if not internal_path.startswith("scripts/"):
            internal_path = f"scripts/{internal_path}"
            
        try:
            if self.mode == 'zip':
                with self.source.open(internal_path) as f:
                    return f.read().decode('utf-8', errors='replace')
            else:
                real_path = os.path.join(self.source, internal_path.replace("scripts/", ""))
                if os.path.exists(real_path):
                    with open(real_path, 'r', encoding='utf-8') as f:
                        return f.read()
        except KeyError:
            return None 
        except FileNotFoundError:
            return None
        return None

    def load_tuning_db(self):
        """核心逻辑：解析 tuning.lua 构建数值字典 (宽容模式)"""
        console.print("[dim]⚡ 正在构建 Tuning 数值库...[/dim]")
        content = self.read_file("tuning.lua")
        if not content:
            console.print("[red]⚠️ 警告: 无法读取 tuning.lua[/red]")
            return

        # [升级版正则] 
        # 不再只匹配数字，而是匹配等号后面直到逗号或换行的所有内容
        # group(1): 变量名
        # group(2): 值 (可能是数字、公式、字符串)
        pattern = re.compile(r'([A-Z0-9_]+)\s*=\s*([^,\r\n]+)')
        
        count = 0
        for name, raw_value in pattern.findall(content):
            key = f"TUNING.{name}"
            # 清理注释 (例如: 34 --damage)
            clean_val = raw_value.split('--')[0].strip()
            
            # 尝试转数字，转不了就存字符串
            try:
                self.tuning_data[key] = float(clean_val)
            except ValueError:
                self.tuning_data[key] = clean_val # 存原始文本 (如 "34 * 1")
            
            count += 1
        
        console.print(f"[green]✅ 索引完成: {len(self.tuning_data)} 条常量[/green]")

    def resolve_val(self, val_str):
        """将代码变量 (TUNING.X) 转换为 真实数值"""
        val_str = val_str.strip()
        # 如果是纯数字，直接返回
        try:
            return str(float(val_str))
        except ValueError:
            pass
        
        # 查表
        if val_str in self.tuning_data:
            val = self.tuning_data[val_str]
            # 如果是数字，显示青色；如果是文本(公式)，显示黄色
            color = "bold cyan" if isinstance(val, float) else "yellow"
            return f"[{color}]{val}[/{color}] [dim]({val_str})[/dim]"
            
        return f"{val_str} [dim](?)[/dim]"

    def search_recipe(self, item):
        """从 recipes.lua 提取配方"""
        content = self.read_file("recipes.lua")
        if not content: return None

        pattern = re.compile(r'Recipe\s*\(\s*["\']' + re.escape(item) + r'["\']\s*,\s*\{(.*?)\}', re.DOTALL)
        match = pattern.search(content)
        
        if match:
            raw_ing = match.group(1)
            ings = re.findall(r'Ingredient\s*\(\s*["\'](.*?)["\']\s*,\s*([0-9\.]+)', raw_ing)
            return ings
        return None

    def analyze_prefab(self, item):
        """深度扫描 Prefab 文件，提取 Weapon/Armor/Edible 信息"""
        content = self.read_file(f"prefabs/{item}.lua")
        if not content: return None
        
        info = {}

        # 1. ⚔️ 武器组件
        dmg = re.search(r'components\.weapon:SetDamage\s*\((.*?)\)', content)
        if dmg: info['⚔️ 攻击力'] = self.resolve_val(dmg.group(1))

        # 2. 🛡️ 护甲组件
        armor = re.search(r'components\.armor:InitCondition\s*\((.*?),\s*(.*?)\)', content)
        if armor:
            info['🛡️ 耐久度'] = self.resolve_val(armor.group(1))
            info['🛡️ 减伤率'] = self.resolve_val(armor.group(2))

        # 3. 🍖 食物组件
        if "components.edible" in content:
            hv = re.search(r'edible\.healthvalue\s*=\s*(.*)', content)
            hung = re.search(r'edible\.hungervalue\s*=\s*(.*)', content)
            san = re.search(r'edible\.sanityvalue\s*=\s*(.*)', content)
            
            if hv: info['❤️ 生命'] = self.resolve_val(hv.group(1))
            if hung: info['🍖 饥饿'] = self.resolve_val(hung.group(1))
            if san: info['🧠 San'] = self.resolve_val(san.group(1))

        return info

def main():
    if len(sys.argv) < 2:
        console.print("[yellow]用法: python wiki.py <物品代码>[/yellow]")
        return

    target = sys.argv[1].lower()
    wiki = DSTWiki()
    
    console.print(Panel(f"[bold white on blue] 📚 正在查询档案: {target.upper()} [/bold white on blue]"))

    # 并行获取数据
    recipe = wiki.search_recipe(target)
    stats = wiki.analyze_prefab(target)

    if not recipe and not stats:
        console.print(f"[red]❌ 未找到 '{target}' 的有效记录。[/red]")
        console.print("[dim]提示: 请使用代码名 (如 log, spear, meat)[/dim]")
        return

    # === 渲染结果 ===
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column()
    grid.add_column()

    # 左列：配方
    if recipe:
        rt = Table(title="📜 合成配方", border_style="green", box=box.ROUNDED)
        rt.add_column("材料", style="cyan")
        rt.add_column("数量", style="magenta")
        for name, amt in recipe:
            rt.add_row(name, str(int(float(amt))))
        grid.add_row(rt, "")
    else:
        grid.add_row(Panel("[dim]不可合成 / 特殊配方[/dim]", title="📜 合成配方"), "")

    # 右列：属性
    if stats:
        st = Table(title="⚡ 核心数据 (解析后)", border_style="blue", box=box.ROUNDED)
        st.add_column("属性", style="white")
        st.add_column("数值", style="yellow")
        for k, v in stats.items():
            st.add_row(k, v)
        grid.add_row("", st)
    
    if stats:
        console.print(st)

if __name__ == "__main__":
    main()
