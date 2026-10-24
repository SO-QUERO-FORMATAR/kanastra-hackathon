import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping


def normalize_document(value: str) -> str:
    """Remove only known formatting; never discard letters or repair check digits."""
    return value.translate(str.maketrans("", "", "./- "))


def document_root(value: str) -> str | None:
    value = normalize_document(value)
    return value[:8] if re.fullmatch(r"[0-9]{14}", value) else None


def cnpj_valid(value: str) -> bool:
    value = normalize_document(value)
    if not re.fullmatch(r"[0-9]{14}", value) or len(set(value)) == 1:
        return False
    for length, weights in [
        (12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
        (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
    ]:
        remainder = sum(int(d) * w for d, w in zip(value[:length], weights)) % 11
        if int(value[length]) != (0 if remainder < 2 else 11 - remainder):
            return False
    return True


@dataclass(frozen=True)
class Fund:
    id: str
    name: str
    document: str


@dataclass(frozen=True)
class Origin:
    lot_id: str
    file_id: str
    line: int
    sequence: int


@dataclass(frozen=True)
class Title:
    fund: Fund
    origin: Origin
    seller_name: str
    seller_document: str
    debtor_name: str
    debtor_document: str
    number: str
    receivable_type: str
    nominal: Decimal
    acquisition_date: date
    due_date: date
    original: Mapping[str, str | None]

    @property
    def days(self) -> int:
        return (self.due_date - self.acquisition_date).days

    @property
    def operational_key(self) -> tuple[str, str, str]:
        return normalize_document(self.seller_document), normalize_document(self.debtor_document), self.number


@dataclass(frozen=True)
class Reason:
    code: str
    message: str
    observed: str | None = None
    limit: str | None = None


@dataclass(frozen=True)
class Decision:
    title: Title
    reasons: tuple[Reason, ...]
    discount: Decimal = Decimal("0.00")
    net: Decimal = Decimal("0.00")

    @property
    def approved(self) -> bool:
        return not self.reasons
