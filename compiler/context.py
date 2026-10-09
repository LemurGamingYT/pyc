from dataclasses import dataclass, field
from typing import Optional, TypeAlias
from enum import Enum, auto


PyType: TypeAlias = type

class SymbolKind(Enum):
    VARIABLE = auto()
    FUNCTION = auto()

@dataclass(slots=True)
class Symbol:
    type: PyType
    kind: SymbolKind

@dataclass(slots=True)
class Scope:
    parent: Optional['Scope'] = None
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def clone(self):
        return Scope(self, self.symbols.copy())
