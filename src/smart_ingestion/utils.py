import re
from pathlib import Path

from smart_ingestion.config import ALLOWED_READ_ROOTS, ALLOWED_WRITE_ROOTS, PROJECT_ROOT


def sanitize_table_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", name)
    if not cleaned:
        raise ValueError("Invalid table name")
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned


def resolve_read_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    _assert_under_allowed(path, ALLOWED_READ_ROOTS)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    return path


def resolve_write_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    _assert_under_allowed(path, ALLOWED_WRITE_ROOTS)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _assert_under_allowed(path: Path, roots: tuple[Path, ...]) -> None:
    for root in roots:
        root = root.resolve()
        try:
            path.relative_to(root)
            return
        except ValueError:
            continue
    allowed = ", ".join(str(r) for r in roots)
    raise PermissionError(f"Path '{path}' is outside allowed directories: {allowed}")
