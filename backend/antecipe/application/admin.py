from pathlib import Path
from antecipe.ports.admin import AdminRepository


class Admin:
    def __init__(self, repository: AdminRepository):
        self.repository = repository

    def import_registry(self, path: Path) -> str:
        return self.repository.import_registry(path)

    def import_rules(self, path: Path) -> tuple[str, str]:
        return self.repository.import_rules(path)

    def discover_fund(self, cnpj: str, name: str) -> str:
        return self.repository.discover_fund(cnpj, name)

    def get_rules(self, fund_id: str, version: str | None = None) -> dict | None:
        return self.repository.get_rules(fund_id, version)

    def publish_rules(self, fund_id: str, data: dict, base: str | None) -> str:
        return self.repository.publish_rules(fund_id, data, base)

    def situations(self, load_id: str, documents: set[str]) -> dict[str, str]:
        return self.repository.situations(load_id, documents)
