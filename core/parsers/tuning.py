# -*- coding: utf-8 -*-
"""Tuning resolver for DST tuning.lua."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from core.lua import _NUM_RE, _split_top_level, find_matching, parse_lua_expr, parse_lua_string, strip_lua_comments

__all__ = ["TuningResolver"]


_ARITH_TOKEN_RE = re.compile(r"\s*(\d+\.\d+|\d+|[A-Za-z_][A-Za-z0-9_\.]*|\*\*|\^|[+\-*/()])\s*")


class TuningResolver:
    """
    Lightweight resolver for DST `scripts/tuning.lua`.

    Goals
    - Parse common constant assignments:
        - `local NAME = <rhs>`  (UPPER_CASE only)
        - `TUNING.NAME = <rhs>`
    - Resolve numeric chains and simple arithmetic expressions.
    - Provide *traceable* resolution (for UI/wiki), not only final numbers.

    Notes
    - This is intentionally conservative: if an expression can't be proven safe and numeric,
      resolution returns None rather than guessing.
    """

    _REF_PAT = re.compile(r"TUNING\.([A-Za-z0-9_]+)|TUNING\[\s*([\'\"])([A-Za-z0-9_]+)\2\s*\]")

    def __init__(self, content: str):
        self.raw_map: Dict[str, Any] = {}
        self.local_map: Dict[str, Any] = {}
        if content:
            self._parse_tuning(content)

    # --------------------------
    # Parsing
    # --------------------------

    def _parse_tuning(self, content: str) -> None:
        clean = strip_lua_comments(content)

        # locals (allow lowercase; many tuning constants depend on lower vars like calories_per_day)
        for m in re.finditer(r"^\s*local\s+([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$", clean, flags=re.MULTILINE):
            name, rhs = m.group(1), m.group(2)
            rhs = rhs.strip().rstrip(",")
            val = self._parse_rhs(rhs)
            if val is not None:
                self.local_map[name] = val

        # TUNING.KEY = rhs
        for m in re.finditer(r"^\s*TUNING\.([A-Z0-9_]+)\s*=\s*(.+?)\s*$", clean, flags=re.MULTILINE):
            key, rhs = m.group(1), m.group(2)
            rhs = rhs.strip().rstrip(",")
            val = self._parse_rhs(rhs)
            self.raw_map[key] = val if val is not None else rhs

        # TUNING = { KEY = rhs, ... }
        for m_table in re.finditer(r"\bTUNING\s*=\s*\{", clean):
            open_idx = clean.find("{", m_table.start())
            close_idx = find_matching(clean, open_idx, "{", "}")
            if close_idx is None:
                continue
            inner = clean[open_idx + 1 : close_idx]
            for m in re.finditer(r"^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*(?:,|$)", inner, flags=re.MULTILINE):
                key, rhs = m.group(1), m.group(2)
                rhs = rhs.strip().rstrip(",")
                val = self._parse_rhs(rhs)
                if key not in self.raw_map:
                    self.raw_map[key] = val if val is not None else rhs

    def _parse_rhs(self, rhs: str) -> Optional[Any]:
        rhs = (rhs or "").strip().rstrip(",")
        if not rhs:
            return None
        if rhs in ("true", "false"):
            return rhs == "true"
        if rhs == "nil":
            return None

        s = parse_lua_string(rhs)
        if s is not None:
            return s

        if _NUM_RE.match(rhs):
            try:
                f = float(rhs)
                return int(f) if f.is_integer() else f
            except Exception:
                return None

        # keep as raw string expression / symbol
        return rhs

    # --------------------------
    # Resolution (internal)
    # --------------------------

    @staticmethod
    def _norm_key(ref: str) -> str:
        ref = (ref or "").strip()
        return ref[7:] if ref.startswith("TUNING.") else ref

    def _resolve_ref(self, ref: str, depth: int = 8) -> Optional[Union[int, float]]:
        """Resolve a ref/expression to a number (or None)."""
        if depth <= 0:
            return None
        ref = (ref or "").strip()
        if not ref:
            return None

        # numeric literal
        if _NUM_RE.match(ref):
            try:
                f = float(ref)
                return int(f) if f.is_integer() else f
            except Exception:
                return None

        # math.* function calls (limited whitelist)
        m_call = re.match(r"^math\.([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", ref)
        if m_call:
            fn = m_call.group(1).lower()
            args_raw = m_call.group(2)
            args: List[Optional[Union[int, float]]] = []
            for part in _split_top_level(args_raw, sep=","):
                part = part.strip()
                if not part:
                    continue
                args.append(self._resolve_ref(part, depth - 1))
            # only proceed if all args resolved
            if any(a is None for a in args):
                return None
            vals = [float(a) for a in args if a is not None]
            try:
                if fn == "abs" and len(vals) == 1:
                    return abs(vals[0])
                if fn == "floor" and len(vals) == 1:
                    return math.floor(vals[0])
                if fn == "ceil" and len(vals) == 1:
                    return math.ceil(vals[0])
                if fn == "sqrt" and len(vals) == 1:
                    return math.sqrt(vals[0])
                if fn == "max" and vals:
                    return max(vals)
                if fn == "min" and vals:
                    return min(vals)
                if fn in ("pow",) and len(vals) == 2:
                    return math.pow(vals[0], vals[1])
            except Exception:
                return None
            return None

        # direct symbol (TUNING.X / local X)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", ref):
            key = self._norm_key(ref)
            v = self.raw_map.get(key, self.local_map.get(key))
            if isinstance(v, (int, float)):
                return v
            if isinstance(v, str) and v and v != ref:
                # symbol chain (A -> B) or expression
                if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", v):
                    return self._resolve_ref(v, depth - 1)
                return self._resolve_ref(v, depth - 1)
            return None

        # arithmetic expression (conservative tokenizer)
        py_parts: List[str] = []
        for tok in _ARITH_TOKEN_RE.findall(ref):
            tok = tok.strip()
            if not tok:
                continue

            # Lua exponent
            if tok == "^":
                py_parts.append("**")
                continue
            if tok in {"+", "-", "*", "/", "(", ")", "**"}:
                py_parts.append(tok)
                continue
            if _NUM_RE.match(tok):
                py_parts.append(tok)
                continue

            val = self._resolve_ref(tok, depth - 1)
            if val is None:
                return None
            py_parts.append(str(val))

        expr_py = "".join(py_parts)
        # Safety: only numbers + operators
        if re.search(r"[^0-9\.\+\-\*\/\(\)eE]", expr_py):
            return None
        try:
            out = eval(expr_py, {"__builtins__": {}}, {})
            if isinstance(out, (int, float)):
                if isinstance(out, float) and out.is_integer():
                    return int(out)
                return out
        except Exception:
            return None
        return None

    # --------------------------
    # Public APIs
    # --------------------------

    def explain(self, key: str, max_hops: int = 10) -> Tuple[str, Optional[Union[int, float]]]:
        """Return (chain_text, resolved_value)."""
        key = self._norm_key(key)
        if not key:
            return "", None

        chain: List[str] = []
        visited = set()
        cur = key

        for _ in range(max_hops):
            if cur in visited:
                chain.append(f"{cur} (loop)")
                break
            visited.add(cur)

            v = self.raw_map.get(cur, self.local_map.get(cur))
            if v is None:
                chain.append(cur)
                break

            chain.append(cur)

            if isinstance(v, (int, float)):
                chain.append(str(v))
                return " -> ".join(chain), v

            if isinstance(v, str):
                chain.append(v)
                if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", v):
                    cur = self._norm_key(v)
                    continue
                val = self._resolve_ref(v)
                if val is not None:
                    chain.append(str(val))
                    return " -> ".join(chain), val
                break

            chain.append(str(v))
            break

        # fallback try resolve the symbol itself (handles local->expr cases)
        val = self._resolve_ref(key)
        return " -> ".join(chain) if chain else key, val

    def trace_key(self, key: str, max_hops: int = 16) -> Dict[str, Any]:
        """Structured trace for a single TUNING key."""
        key0 = key
        key = self._norm_key(key)
        steps: List[Dict[str, Any]] = []
        visited = set()
        cur = key

        for _ in range(max_hops):
            if not cur:
                break
            if cur in visited:
                steps.append({"key": cur, "raw": None, "note": "loop"})
                break
            visited.add(cur)

            v = self.raw_map.get(cur, self.local_map.get(cur))
            steps.append({"key": cur, "raw": v})

            if isinstance(v, (int, float)):
                chain = " -> ".join([str(s.get("key") or "") for s in steps] + [str(v)])
                return {"key": key0, "normalized": key, "value": v, "steps": steps, "chain": chain}

            if isinstance(v, str) and re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", v):
                cur = self._norm_key(v)
                continue

            # expression or unknown
            if isinstance(v, str):
                val = self._resolve_ref(v)
                return {
                    "key": key0,
                    "normalized": key,
                    "value": val,
                    "steps": steps + [{"key": "<expr>", "raw": v, "value": val}],
                    "chain": " -> ".join([str(s.get("key") or s.get("raw") or "") for s in steps] + [v, str(val)]),
                }
            break

        # fallback
        val = self._resolve_ref(key)
        return {
            "key": key0,
            "normalized": key,
            "value": val,
            "steps": steps,
            "chain": " -> ".join([str(s.get("key") or s.get("raw") or "") for s in steps if s.get("key")] + ([str(val)] if val is not None else [])),
        }

    def trace_expr(self, expr: str) -> Dict[str, Any]:
        """Trace an arbitrary expression containing TUNING refs."""
        expr = (expr or "").strip()
        refs = []
        for m in self._REF_PAT.finditer(expr):
            k = m.group(1) or m.group(3)
            if k and k not in refs:
                refs.append(k)

        ref_traces: Dict[str, Any] = {}
        for k in refs:
            ref_traces[k] = self.trace_key(k)

        value = self._resolve_ref(expr)

        # best-effort normalized expression (TUNING.X -> number)
        expr_resolved = expr
        for k in refs:
            v = ref_traces.get(k, {}).get("value")
            if isinstance(v, (int, float)):
                expr_resolved = re.sub(
                    rf"\bTUNING\.{re.escape(k)}\b",
                    str(v),
                    expr_resolved,
                )
                expr_resolved = re.sub(
                    rf"TUNING\[\s*([\'\"])\s*{re.escape(k)}\s*\1\s*\]",
                    str(v),
                    expr_resolved,
                )

        return {
            "expr": expr,
            "value": value,
            "expr_resolved": expr_resolved,
            "refs": ref_traces,
            "expr_chain": " ; ".join(sorted([rt.get("chain") or "" for rt in ref_traces.values() if rt])),
        }

    def enrich(self, text: str) -> str:
        """Inline enrichment: replace `TUNING.X` in text with `TUNING.X (chain)` when resolvable."""
        if not text or "TUNING" not in text:
            return text

        def repl(m: re.Match) -> str:
            key = m.group(1) or m.group(3)
            if not key:
                return m.group(0)
            chain, val = self.explain(key)
            if val is None:
                return f"TUNING.{key}"
            return f"TUNING.{key} ({chain})"

        return self._REF_PAT.sub(repl, text)
