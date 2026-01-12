#!/usr/bin/env python3
import re

# ==========================================
# 1. 全局数值解析器 (TuningResolver)
# ==========================================
class TuningResolver:
    def __init__(self, content):
        self.raw_map = {}
        if content:
            self._parse_tuning(content)

    def _parse_tuning(self, content):
        clean_content = re.sub(r'\blocal\s+', '', content)
        pattern = re.compile(r'([a-zA-Z0-9_]+)\s*=\s*([^,\r\n]+)')
        for name, raw_val in pattern.findall(clean_content):
            clean_val = raw_val.split('--')[0].strip()
            try:
                self.raw_map[name] = float(clean_val)
            except ValueError:
                self.raw_map[name] = clean_val

    def _trace_value(self, start_key):
        path = []
        current_key = start_key
        visited = set()
        for _ in range(5):
            if current_key in visited: break
            visited.add(current_key)
            val = self.raw_map.get(current_key)
            if val is None: break
            if isinstance(val, float):
                path.append(f"[bold cyan]{val}[/bold cyan]")
                break
            if isinstance(val, str):
                if val in self.raw_map:
                    path.append(f"[yellow]{val}[/yellow]")
                    current_key = val
                else:
                    path.append(f"[white]{val}[/white]")
                    break
        if not path: return None
        return " ➜ ".join(path)

    def enrich(self, text):
        if not text or "TUNING." not in text: return text
        def replace_match(match):
            full_key = match.group(1)
            short_key = full_key.replace("TUNING.", "")
            trace_str = self._trace_value(short_key)
            if trace_str:
                return f"{full_key} [dim]({trace_str})[/dim]"
            return full_key
        return re.sub(r'(TUNING\.[A-Z0-9_]+)', replace_match, text)

# ==========================================
# 2. Lua 文件分析器 (LuaAnalyzer)
# ==========================================
class LuaAnalyzer:
    def __init__(self, content):
        self.content = content
        self.structure = {
            "assets": [], "components": [], "helpers": [],
            "stategraph": None, "brain": None, "events": [], "tags": []
        }
        self.parse()

    def parse(self):
        self._extract_tables()
        self._extract_components_robust()
        self._extract_standard_helpers()
        self._extract_logic()

    def _clean_value(self, raw_val):
        val = re.sub(r'--.*', '', raw_val)
        return " ".join(val.split())

    def _extract_tables(self):
        asset_pattern = re.compile(r'Asset\s*\(\s*["\'](.*?)["\']\s*,\s*["\'](.*?)["\']\s*\)')
        for match in asset_pattern.findall(self.content):
            self.structure["assets"].append({"type": match[0], "path": match[1]})

    def _extract_standard_helpers(self):
        helper_pattern = re.compile(r'^\s*(Make[a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
        found = set()
        for match in helper_pattern.findall(self.content):
            if match not in found:
                self.structure["helpers"].append(match)
                found.add(match)

    def _extract_components_robust(self):
        added_comps = set()
        add_pattern = re.compile(r'inst:AddComponent\s*\(\s*["\'](.*?)["\']\s*\)')
        for match in add_pattern.findall(self.content):
            added_comps.add(match)
        for comp_name in added_comps:
            comp_data = {"name": comp_name, "methods": [], "properties": []}
            method_pattern = re.compile(r'components\.' + re.escape(comp_name) + r'[:\.]([a-zA-Z0-9_]+)\s*\((.*?)\)', re.DOTALL)
            for m in method_pattern.findall(self.content):
                func_name = m[0]
                clean_args = self._clean_value(m[1])
                if len(clean_args) > 50: clean_args = clean_args[:47] + "..."
                comp_data["methods"].append(f"{func_name}({clean_args})")
            prop_pattern = re.compile(r'components\.' + re.escape(comp_name) + r'\.([a-zA-Z0-9_]+)\s*=\s*(.+)')
            for p in prop_pattern.findall(self.content):
                prop_name = p[0]
                raw_val = p[1].strip()
                if raw_val.startswith("function"):
                    comp_data["properties"].append(f"{prop_name} = [Function]")
                    continue
                clean_val = self._clean_value(raw_val)
                comp_data["properties"].append(f"{prop_name} = {clean_val}")
            self.structure["components"].append(comp_data)

    def _extract_logic(self):
        brain = re.search(r'inst:SetBrain\s*\(\s*require\s*\(\s*["\'](.*?)["\']\s*\)\s*\)', self.content)
        if brain: self.structure["brain"] = brain.group(1)
        sg = re.search(r'inst:SetStateGraph\s*\(\s*["\'](.*?)["\']\s*\)', self.content)
        if sg: self.structure["stategraph"] = sg.group(1)
        tags = re.findall(r'[^--]inst:AddTag\s*\(\s*["\'](.*?)["\']\s*\)', self.content)
        self.structure["tags"] = list(set(tags))
        events = re.findall(r'inst:ListenForEvent\s*\(\s*["\'](.*?)["\']', self.content)
        self.structure["events"] = list(set(events))

    def get_report(self):
        return self.structure

# ==========================================
# 3. 配方解析器 (RecipeAnalyzer) - [FINAL]
# ==========================================
class RecipeAnalyzer:
    def __init__(self, content):
        self.raw_content = content
        self.recipes = {}
        self.aliases = {}
        if content:
            self._parse()

    def _clean_comments(self):
        return re.sub(r'--.*$', '', self.raw_content, flags=re.MULTILINE)

    def _extract_table_block(self, content, start_index):
        # 堆栈式提取 {...}
        start_brace = content.find('{', start_index)
        if start_brace == -1: return None, start_index

        balance = 1
        for i in range(start_brace + 1, len(content)):
            char = content[i]
            if char == '{':
                balance += 1
            elif char == '}':
                balance -= 1
            if balance == 0:
                return content[start_brace+1 : i], i + 1
        return None, start_index

    def _parse(self):
        clean_content = self._clean_comments()
        
        # [核心修复]
        # 1. \bRecipe: 确保匹配单词开头，排除 DeconstructRecipe
        # 2. 2?: 兼容 Recipe 和 Recipe2
        # 3. \(: 确保是函数调用
        iter_pattern = re.compile(r'\bRecipe2?\s*\(\s*["\'](.*?)["\']', re.DOTALL)
        
        for match in iter_pattern.finditer(clean_content):
            name = match.group(1)
            cursor = match.end()
            
            # 提取成分表
            ing_block, new_cursor = self._extract_table_block(clean_content, cursor)
            
            if ing_block:
                ingredients = []
                # 解析 Ingredient
                ing_pattern = re.compile(r'Ingredient\s*\(\s*["\'](.*?)["\']\s*,\s*([^,\)]+)')
                for item, amount in ing_pattern.findall(ing_block):
                    ingredients.append({"item": item, "amount": amount.strip()})
                
                # 尝试提取后续参数 (Tab, Tech)
                remainder = clean_content[new_cursor:].split(')')[0]
                parts = [p.strip() for p in remainder.split(',') if p.strip()]
                
                # Recipe 和 Recipe2 的参数位置略有不同，但通常 Tab 和 Tech 都在前面
                # 这里做个简单的防御式提取
                tab = "UNKNOWN"
                tech = "UNKNOWN"
                
                for p in parts:
                    if "TECH." in p: tech = p
                    if "RECIPETABS." in p: tab = p

                self.recipes[name] = {
                    "ingredients": ingredients,
                    "tab": tab,
                    "tech": tech
                }
                
                # 建立索引
                self.aliases[name.lower()] = name
                self.aliases[name.replace("_", "").lower()] = name

    def get(self, query_name):
        q = query_name.lower()
        real_name = self.aliases.get(q)
        if not real_name:
            real_name = self.aliases.get(q.replace("_", ""))
        
        if real_name:
            return real_name, self.recipes[real_name]
        return None, None