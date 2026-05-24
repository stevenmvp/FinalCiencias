from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class StorageManager:
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.base_path / "catalog.json"

    def _atomic_write_json(self, path: Path, data: Any) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=True, indent=2)
        os.replace(tmp_path, path)

    def load_catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return {"tables": {}}
        with self.catalog_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def save_catalog(self, catalog: dict[str, Any]) -> None:
        self._atomic_write_json(self.catalog_path, catalog)

    def table_path(self, table_name: str) -> Path:
        return self.base_path / f"{table_name}.json"

    def load_table_rows(self, table_name: str) -> list[dict[str, Any]]:
        t_path = self.table_path(table_name)
        if not t_path.exists():
            return []
        with t_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def save_table_rows(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        self._atomic_write_json(self.table_path(table_name), rows)

    def delete_table(self, table_name: str) -> None:
        t_path = self.table_path(table_name)
        if t_path.exists():
            t_path.unlink()
