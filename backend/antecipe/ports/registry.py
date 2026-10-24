from typing import Protocol


class Registry(Protocol):
    def situations(self, documents: set[str]) -> dict[str, str]: ...
