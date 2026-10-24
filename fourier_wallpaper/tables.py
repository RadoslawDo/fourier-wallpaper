"""Values read from the TOML files, as the type checker sees them: anything until checked."""
from typing import Any, TypeGuard

Table = dict[str, Any]                   # a TOML table


def is_table(v: object) -> TypeGuard[Table]:
    return isinstance(v, dict)


def is_list(v: object) -> TypeGuard[list[Any]]:
    return isinstance(v, list)
