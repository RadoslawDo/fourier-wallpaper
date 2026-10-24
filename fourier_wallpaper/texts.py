"""Helpers for the texts from languages/<code>.toml."""


def plural(n, lang):
    """The word "circle" after a number, by the language's plural rule."""
    forms = lang["circle"]
    if lang["plural_rule"] == "pl":
        return forms[0] if n == 1 else forms[1] if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else forms[2]
    return forms[0] if n == 1 else forms[1]
