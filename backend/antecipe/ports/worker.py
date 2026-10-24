from typing import Protocol


class WorkerRepository(Protocol):
    def run_once(self) -> bool: ...
