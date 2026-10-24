"""Read a supplied input without relying on its basename or extracting ZIP paths."""

from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def read_input(path: Path, member: str | None = None) -> tuple[str, bytes]:
    if path.suffix.lower() != ".zip":
        if member is not None:
            raise ValueError("--member só pode ser usado com ZIP")
        if path.suffix.lower() not in {".csv", ".xlsx"}:
            raise ValueError("Esperado arquivo CSV, XLSX ou ZIP")
        return path.name, path.read_bytes()
    with ZipFile(path) as archive:
        candidates = [
            info
            for info in archive.infolist()
            if not info.is_dir()
            and PurePosixPath(info.filename).suffix.lower() in {".csv", ".xlsx"}
            and (member is None or info.filename == member)
        ]
        if len(candidates) != 1:
            raise ValueError("ZIP deve selecionar exatamente um CSV/XLSX; informe --member se necessário")
        selected = candidates[0]
        return PurePosixPath(selected.filename).name, archive.read(selected)
