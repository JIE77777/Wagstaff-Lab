#!/usr/bin/env python3
import os
import zipfile
from rich.console import Console
from utils import wagstaff_config
from analyzer import TuningResolver, RecipeAnalyzer, LuaAnalyzer

console = Console()

class WagstaffEngine:
    """
    Wagstaff Lab 核心引擎 (v1.0)
    职责: 统一管理数据源 (Zip/Folder) 和 核心知识库 (Tuning/Recipes)
    """
    def __init__(self, load_db=True, silent=False):
        self.base_dir = wagstaff_config.get('PATHS', 'DST_ROOT')
        self.zip_path = os.path.join(self.base_dir, "data", "databundles", "scripts.zip")
        self.fallback_dir = os.path.join(self.base_dir, "data", "scripts")
        
        self.mode = None
        self.source = None
        self.file_list = []
        
        self.tuning = None
        self.recipes = None
        
        self._init_source(silent)
        if load_db:
            self._init_databases(silent)

    def _init_source(self, silent):
        if os.path.exists(self.zip_path):
            self.mode = 'zip'
            self.source = zipfile.ZipFile(self.zip_path, 'r')
            self.file_list = self.source.namelist()
            if not silent: console.print(f"[dim]📦 引擎挂载 Zip 源: {self.zip_path}[/dim]")
        elif os.path.exists(self.fallback_dir):
            self.mode = 'folder'
            self.source = self.fallback_dir
            for root, _, files in os.walk(self.fallback_dir):
                for name in files:
                    rel = os.path.relpath(os.path.join(root, name), self.fallback_dir).replace("\\", "/")
                    self.file_list.append(rel)
            if not silent: console.print(f"[dim]📂 引擎挂载文件夹源: {self.fallback_dir}[/dim]")
        else:
            raise FileNotFoundError("无法找到 scripts.zip 或 scripts/ 目录")

    def _init_databases(self, silent):
        if not silent: console.print("[dim]🔄 加载神经中枢 (Tuning & Recipes)...[/dim]")
        t_content = self.read_file("scripts/tuning.lua") or self.read_file("tuning.lua")
        self.tuning = TuningResolver(t_content if t_content else "")
        r_content = self.read_file("scripts/recipes.lua") or self.read_file("recipes.lua")
        self.recipes = RecipeAnalyzer(r_content if r_content else "")

    def read_file(self, path):
        """智能读取文件（自动处理 scripts/ 前缀）"""
        candidates = [path]
        if not path.startswith("scripts/"): candidates.append(f"scripts/{path}")
        else: candidates.append(path.replace("scripts/", ""))
        
        try:
            if self.mode == 'zip':
                for p in candidates:
                    if p in self.file_list:
                        return self.source.read(p).decode('utf-8', errors='replace')
            else:
                for p in candidates:
                    real_path = os.path.join(self.source, p.replace("scripts/", ""))
                    if os.path.exists(real_path):
                        with open(real_path, 'r', encoding='utf-8', errors='replace') as f: return f.read()
        except Exception:
            return None
        return None

    def find_file(self, name, fuzzy=True):
        """模糊查找文件 (如 armorwood -> scripts/prefabs/armor_wood.lua)"""
        candidates = [f"scripts/prefabs/{name}.lua", f"prefabs/{name}.lua", f"scripts/{name}", name]
        for c in candidates:
            if c in self.file_list: return c
            
        if not fuzzy: return None

        target = name.replace("_", "").lower()
        for fname in self.file_list:
            if not fname.endswith(".lua"): continue
            base = os.path.basename(fname).replace(".lua", "")
            if base.replace("_", "").lower() == target:
                return fname
        return None

    def analyze_prefab(self, item_name):
        """一键分析 Prefab (整合了 wiki.py 的逻辑)"""
        path = self.find_file(item_name)
        if not path: return None
        
        content = self.read_file(path)
        if not content: return None
        
        analyzer = LuaAnalyzer(content)
        data = analyzer.get_report()
        
        if self.tuning:
            for comp in data.get('components', []):
                comp['properties'] = [self.tuning.enrich(p) for p in comp['properties']]
                comp['methods'] = [self.tuning.enrich(m) for m in comp['methods']]
        
        return data
