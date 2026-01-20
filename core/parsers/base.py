# -*- coding: utf-8 -*-
"""Base classes for domain parsers."""

from __future__ import annotations

import re
from typing import List, Optional

from core.lua import strip_lua_comments

__all__ = ["BaseParser"]


class BaseParser:
    def __init__(self, content: str, path: Optional[str] = None):
        self.path = path
        self.content = content or ""
        self.clean = strip_lua_comments(self.content)

    def _extract_requires(self) -> List[str]:
        return re.findall(r'require\s*\(?\s*["\'](.*?)["\']\s*\)?', self.clean)
