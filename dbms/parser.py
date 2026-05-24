from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Condition:
    field: str
    op: str
    value: Any
    second_value: Any = None


def split_csv(text: str) -> list[str]:
    parts: list[str] = []
    buf = []
    quote = None
    for ch in text:
        if ch in ("'", '"'):
            if quote is None:
                quote = ch
            elif quote == ch:
                quote = None
            buf.append(ch)
            continue
        if ch == "," and quote is None:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def parse_value(raw: str) -> Any:
    token = raw.strip()
    if re.fullmatch(r"'.*'|\".*\"", token):
        return token[1:-1]

    low = token.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)
    return token


def parse_condition(where_text: str | None) -> Condition | None:
    if where_text is None:
        return None
    where = where_text.strip().rstrip(";")

    m_between = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*)\s+BETWEEN\s+(.+)\s+AND\s+(.+)",
        where,
        flags=re.IGNORECASE,
    )
    if m_between:
        return Condition(
            field=m_between.group(1),
            op="between",
            value=parse_value(m_between.group(2)),
            second_value=parse_value(m_between.group(3)),
        )

    m_eq = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", where)
    if m_eq:
        return Condition(field=m_eq.group(1), op="eq", value=parse_value(m_eq.group(2)))

    m_cmp = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|>|<)\s*(.+)", where)
    if m_cmp:
        op_map = {">": "gt", "<": "lt", ">=": "gte", "<=": "lte"}
        return Condition(
            field=m_cmp.group(1),
            op=op_map[m_cmp.group(2)],
            value=parse_value(m_cmp.group(3)),
        )

    raise ValueError(
        "WHERE no soportado. Use: campo = valor, campo > valor, campo < valor, "
        "campo >= valor, campo <= valor, o campo BETWEEN a AND b"
    )
