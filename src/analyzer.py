#!/usr/bin/env python3
import re

# ==========================================
# 1. 全局数值解析器 (TuningResolver) - [链式追踪版]
# ==========================================
class TuningResolver:
    def __init__(self, content):
        self.raw_map = {}
        if content:
            self._parse_tuning(content)

    def _parse_tuning(self, content):
        clean_content = re.sub(r'\blocal\s+', '', content)
        # 匹配 NAME = VALUE
        pattern = re.compile(r'([a-zA-Z0-9_]+)\s*=\s*([^,\r\n]+)')
        for name, raw_val in pattern.findall(clean_content):
            # 去除注释和空白
            clean_val = raw_val.split('--')[0].strip()
            
            # 尝试直接转数字
            try:
                self.raw_map[name] = float(clean_val)
            except ValueError:
                # 存为字符串，可能是引用其他变量
                self.raw_map[name] = clean_val

    def enrich(self, text):
        if not text or "TUNING." not in text: return text
        
        def replace_match(match):
            root_key = match.group(1).replace("TUNING.", "")
            
            # === 链式追踪逻辑 Start ===
            chain = []
            current_key = root_key
            visited = {root_key}
            
            # 最多追踪 5 层，防止死循环
            for _ in range(5):
                val = self.raw_map.get(current_key)
                
                # 1. 如果没找到值，停止
                if val is None:
                    break
                
                # 2. 如果是数字，这是终点
                if isinstance(val, (int, float)):
                    if isinstance(val, float) and val.is_integer():
                        val = int(val)
                    chain.append(f"[bold cyan]{val}[/bold cyan]") # 最终数值高亮
                    break
                
                # 3. 如果是字符串
                if isinstance(val, str):
                    # 3a. 如果这个字符串也是个变量名（在表中存在），继续追踪
                    if val in self.raw_map and val not in visited:
                        chain.append(f"[dim]{val}[/dim]") # 中间变量变暗
                        current_key = val
                        visited.add(val)
                    # 3b. 只是普通字符串字面量
                    else:
                        chain.append(f"[green]'{val}'[/green]")
                        break
            # === 链式追踪逻辑 End ===

            if chain:
                # 将路径用 -> 连接，例如: (wilson_attack -> 34)
                chain_str = " -> ".join(chain)
                return f"{match.group(1)} ({chain_str})"
            
            return match.group(1)
            
        return re.sub(r'(TUNING\.[A-Z0-9_]+)', replace_match, text)


# ==========================================
# 2. 专用解析器策略 (Parsers)
# ==========================================

class BaseParser:
    def __init__(self, content):
        self.content = content
        # 预处理：移除注释以便正则匹配，同时保留换行以维持结构感
        self.clean_content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        self.clean_content = re.sub(r'--\[\[.*?\]\]', '', self.clean_content, flags=re.DOTALL)

    def _extract_requires(self):
        return re.findall(r'require\s*[\("\'](.*?)[\)"\']', self.clean_content)

class LootParser(BaseParser):
    """解析掉落表 (LootTables) - v2.0 增强版"""
    def parse(self):
        data = {
            "type": "loot",
            "table_name": None,
            "entries": []
        }
        
        # 1. 提取表名定义 (SetSharedLootTable)
        table_match = re.search(r'SetSharedLootTable\s*\(\s*[\'"]([^\'"]+)[\'"]', self.clean_content)
        if table_match:
            data["table_name"] = table_match.group(1)

        # 2. [新增] 提取内联表定义 (Inline Table Data)
        # 针对 Krampus 这种直接在 SetSharedLootTable 中传入列表的情况
        if data["table_name"]:
            start_idx = self.clean_content.find("SetSharedLootTable")
            if start_idx != -1:
                snippet = self.clean_content[start_idx:]
                # 匹配: { 'prefab', number }
                inline_matches = re.findall(r'\{\s*[\'"]([^\'"]+)[\'"]\s*,\s*([\d\.]+)\s*\}', snippet)
                for item, chance in inline_matches:
                    data["entries"].append({"item": item, "chance": float(chance), "method": "TableData"})

        # 3. 提取随机掉落 (AddRandomLoot)
        for p, w in re.findall(r'AddRandom.*?Loot\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([\d\.]+)', self.clean_content):
            data["entries"].append({"item": p, "weight": float(w), "method": "Random"})

        # 4. 提取概率掉落 (AddChanceLoot)
        for p, c in re.findall(r'AddChanceLoot\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([\d\.]+)', self.clean_content):
            data["entries"].append({"item": p, "chance": float(c), "method": "Chance"})

        return data

class WidgetParser(BaseParser):
    """解析 UI 组件 (Widgets/Screens)"""
    def parse(self):
        data = {
            "type": "widget",
            "classes": [],
            "dependencies": self._extract_requires()
        }

        # 提取类继承关系
        pattern = r'local\s+([a-zA-Z0-9_]+)\s*=\s*Class\s*\(\s*([a-zA-Z0-9_]+)'
        for name, parent in re.findall(pattern, self.clean_content):
            data["classes"].append({"name": name, "parent": parent})

        return data

class StringParser(BaseParser):
    """解析文本配置 (STRINGS)"""
    def parse(self):
        data = {
            "type": "strings",
            "roots": [],
            "includes": self._extract_requires()
        }

        # 提取顶级 Key 定义
        for match in re.findall(r'STRINGS\.([A-Z0-9_]+)\s*=\s*\{', self.clean_content):
            data["roots"].append(match)
        
        # 提取直接赋值
        for match in re.findall(r'STRINGS\.([A-Z0-9_]+)\s*=\s*["\']', self.clean_content):
             if match not in data["roots"]:
                 data["roots"].append(match)

        return data

class PrefabParser(BaseParser):
    """解析实体预设 (Standard Prefabs)"""
    def parse(self):
        data = {
            "type": "prefab",
            "assets": [], "components": [], "helpers": [],
            "stategraph": None, "brain": None, "events": [], "tags": []
        }
        
        # Assets
        for t, p in re.findall(r'Asset\s*\(\s*["\'](.*?)["\']\s*,\s*["\'](.*?)["\']\s*\)', self.clean_content):
            data["assets"].append({"type": t, "path": p})

        # Logic (Brain/SG)
        brain = re.search(r'SetBrain\s*\(\s*require\s*\(\s*["\'](.*?)["\']\s*\)\s*\)', self.clean_content)
        if brain: data["brain"] = brain.group(1)
        
        sg = re.search(r'SetStateGraph\s*\(\s*["\'](.*?)["\']\s*\)', self.clean_content)
        if sg: data["stategraph"] = sg.group(1)

        # Helpers & Tags
        data["helpers"] = list(set(re.findall(r'^\s*(Make[a-zA-Z0-9_]+)\s*\(', self.content, re.MULTILINE)))
        data["tags"] = list(set(re.findall(r'inst:AddTag\s*\(\s*["\'](.*?)["\']\s*\)', self.clean_content)))

        # Components
        added_comps = set(re.findall(r'inst:AddComponent\s*\(\s*["\'](.*?)["\']\s*\)', self.clean_content))
        for comp_name in added_comps:
            comp_data = {"name": comp_name, "methods": [], "properties": []}
            
            # 方法调用
            method_pattern = r'components\.' + re.escape(comp_name) + r'[:\.]([a-zA-Z0-9_]+)\s*\((.*?)\)'
            for m_name, m_args in re.findall(method_pattern, self.clean_content):
                clean_args = re.sub(r'\s+', ' ', m_args).strip()
                if len(clean_args) > 30: clean_args = clean_args[:27] + "..."
                comp_data["methods"].append(f"{m_name}({clean_args})")
            
            # 属性赋值
            prop_pattern = r'components\.' + re.escape(comp_name) + r'\.([a-zA-Z0-9_]+)\s*=\s*([^=\n]+)'
            for p_name, p_val in re.findall(prop_pattern, self.clean_content):
                comp_data["properties"].append(f"{p_name} = {p_val.strip()}")

            data["components"].append(comp_data)
            
        return data

# ==========================================
# 3. 统一分析入口 (Facade)
# ==========================================
class LuaAnalyzer:
    """
    智能分析器：根据文件特征自动选择最佳解析策略
    """
    def __init__(self, content):
        self.content = content
        self.parser = self._select_strategy()

    def _select_strategy(self):
        # 1. Widget/Screen (UI) - 优先级最高
        if "Class(Widget" in self.content or "Class(Screen" in self.content or 'require "widgets/' in self.content:
            return WidgetParser(self.content)
        
        # 2. Prefab (实体) - [关键修复] 优先判定实体
        # 只要包含 "return Prefab"，它就是实体文件，无论里面有没有掉落表定义
        if "return Prefab" in self.content:
            return PrefabParser(self.content)
            
        # 3. Strings (文本)
        if "STRINGS." in self.content and "STRINGS.CHARACTERS" in self.content:
            return StringParser(self.content)

        # 4. Loot Table (纯掉落表文件)
        # 只有在不是 Prefab 的情况下，SetSharedLootTable 才意味着它是纯数据表
        if "SetSharedLootTable" in self.content or "AddChanceLoot" in self.content:
            return LootParser(self.content)
        
        # 5. 默认回退
        return PrefabParser(self.content)

    def get_report(self):
        return self.parser.parse()

# ==========================================
# 4. 配方解析器 (RecipeAnalyzer)
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
        start_brace = content.find('{', start_index)
        if start_brace == -1: return None, start_index
        balance = 1
        for i in range(start_brace + 1, len(content)):
            if content[i] == '{': balance += 1
            elif content[i] == '}': balance -= 1
            if balance == 0: return content[start_brace+1 : i], i + 1
        return None, start_index

    def _parse(self):
        clean_content = self._clean_comments()
        iter_pattern = re.compile(r'\bRecipe2?\s*\(\s*["\'](.*?)["\']', re.DOTALL)
        
        for match in iter_pattern.finditer(clean_content):
            name = match.group(1)
            cursor = match.end()
            ing_block, new_cursor = self._extract_table_block(clean_content, cursor)
            
            if ing_block:
                ingredients = []
                for item, amount in re.findall(r'Ingredient\s*\(\s*["\'](.*?)["\']\s*,\s*([^,\)]+)', ing_block):
                    ingredients.append({"item": item, "amount": amount.strip()})
                
                # [优化] 提取后续参数 (Tab, Tech)
                # 截取直到下一个 Recipe 开始，或者文件结束
                remainder_chunk = clean_content[new_cursor : new_cursor + 300] 
                
                tab = "UNKNOWN"
                tech = "UNKNOWN"
                
                # 提取 TECH.XYZ
                tech_match = re.search(r'(TECH\.[A-Z0-9_]+)', remainder_chunk)
                if tech_match:
                    tech = tech_match.group(1)
                
                # 提取 RECIPETABS.XYZ
                tab_match = re.search(r'(RECIPETABS\.[A-Z0-9_]+)', remainder_chunk)
                if tab_match:
                    tab = tab_match.group(1)

                self.recipes[name] = {"ingredients": ingredients, "tab": tab, "tech": tech}
                self.aliases[name.lower()] = name
                self.aliases[name.replace("_", "").lower()] = name

    def get(self, query_name):
        q = query_name.lower()
        real_name = self.aliases.get(q) or self.aliases.get(q.replace("_", ""))
        return (real_name, self.recipes[real_name]) if real_name else (None, None)