"""Helpers for the texts from languages/<code>.toml."""
from typing import Any

Lang = dict[str, Any]                # languages/<code>.toml


def plural(n: int, lang: Lang) -> str:
    """The word "circle" after a number, by the language's plural rule."""
    forms = lang["circle"]
    if lang["plural_rule"] == "pl":
        return forms[0] if n == 1 else forms[1] if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else forms[2]
    return forms[0] if n == 1 else forms[1]
