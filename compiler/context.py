from typing import Any, Optional, TypeAlias
from dataclasses import dataclass, field
from enum import Enum, auto


PyType: TypeAlias = Any

@dataclass(slots=True)
class Object:
    value: Any
    type: PyType

class SymbolKind(Enum):
    VARIABLE = auto()
    FUNCTION = auto()

@dataclass(slots=True)
class Symbol:
    type: PyType
    kind: SymbolKind
    value: Any

@dataclass(slots=True)
class Scope:
    parent: Optional['Scope'] = None
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def clone(self):
        return Scope(self, self.symbols.copy())
