#!/usr/bin/env python3
import re

class LuaAnalyzer:
    def __init__(self, content):
        self.content = content
        self.lines = content.splitlines()
        self.structure = {
            "assets": [],
            "dependencies": [],
            "components": [],
            "stategraph": None,
            "brain": None,
            "events": [],
            "tags": []
        }
        self.parse()

    def parse(self):
        """执行全量解析"""
        self._extract_tables()
        self._extract_components()
        self._extract_logic()

    def _extract_tables(self):
        """解析 assets 和 prefabs 表"""
        # 1. 提取 Assets
        # 匹配模式: Asset("TYPE", "path")
        asset_pattern = re.compile(r'Asset\s*\(\s*["\'](.*?)["\']\s*,\s*["\'](.*?)["\']\s*\)')
        for match in asset_pattern.findall(self.content):
            self.structure["assets"].append({"type": match[0], "path": match[1]})

        # 2. 提取 Prefab 依赖
        # 这里简化处理，直接找字符串列表
        # 更好的做法是定位 local prefabs = { ... } 区域，但全局搜索通常足够有效
        # 我们假设 prefabs 表里的项通常是纯字符串
        pass # 依赖项通常混杂在代码里，这里暂时主要靠 assets 分析资源

    def _extract_components(self):
        """提取 inst:AddComponent("name") 及其配置"""
        # 这是一个简单的状态机，用于捕获组件及其紧随其后的设置
        
        # 1. 找到所有组件添加的位置
        # matches: [("inspectable"), ("weapon")]
        comp_pattern = re.compile(r'inst:AddComponent\s*\(\s*["\'](.*?)["\']\s*\)')
        
        for match in comp_pattern.finditer(self.content):
            comp_name = match.group(1)
            start_pos = match.end()
            
            # 搜索该组件的配置 (向后搜索 5 行)
            # 例如: inst.components.weapon:SetDamage(34)
            config_extract = []
            lookahead = self.content[start_pos:start_pos+500] # 向后看500字符
            
            # 匹配 inst.components.name:Function(args)
            config_pattern = re.compile(r'components\.' + re.escape(comp_name) + r'[:\.]([a-zA-Z0-9_]+)\s*\((.*?)\)')
            
            for cfg in config_pattern.findall(lookahead):
                func, args = cfg
                # 清理参数中的空白
                args = args.replace('\n', '').strip()
                config_extract.append(f"{func}({args})")
            
            self.structure["components"].append({
                "name": comp_name,
                "configs": config_extract
            })

    def _extract_logic(self):
        """提取 AI、状态图、标签"""
        # Brain
        brain = re.search(r'inst:SetBrain\s*\(\s*require\s*\(\s*["\'](.*?)["\']\s*\)\s*\)', self.content)
        if brain: self.structure["brain"] = brain.group(1)

        # Stategraph
        sg = re.search(r'inst:SetStateGraph\s*\(\s*["\'](.*?)["\']\s*\)', self.content)
        if sg: self.structure["stategraph"] = sg.group(1)

        # Tags (inst:AddTag("xxx"))
        tags = re.findall(r'inst:AddTag\s*\(\s*["\'](.*?)["\']\s*\)', self.content)
        self.structure["tags"] = tags
        
        # ListenForEvent
        events = re.findall(r'inst:ListenForEvent\s*\(\s*["\'](.*?)["\']', self.content)
        self.structure["events"] = list(set(events)) # 去重

    def get_report(self):
        return self.structure
