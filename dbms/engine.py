from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .avl import AVLTree
from .parser import Condition, parse_condition, parse_value, split_csv
from .storage import StorageManager


TYPE_ALIASES = {
    "int": "int",
    "integer": "int",
    "text": "text",
    "real": "real",
    "bool": "bool",
    "boolean": "bool",
}


@dataclass
class Field:
    name: str
    type_name: str
    primary: bool = False


class Table:
    def __init__(self, name: str, fields: list[Field], indexed_fields: list[str] | None = None) -> None:
        self.name = name
        self.fields = fields
        self.field_map = {f.name: f for f in fields}
        self.pk_field = next((f.name for f in fields if f.primary), fields[0].name)
        self.rows: dict[Any, dict[str, Any]] = {}

        idx_set = set(indexed_fields or [])
        idx_set.add(self.pk_field)
        self.indexed_fields = idx_set

        self.pk_index = AVLTree()
        self.secondary_indexes: dict[str, AVLTree] = {
            f: AVLTree() for f in self.indexed_fields if f != self.pk_field
        }

    def to_metadata(self) -> dict[str, Any]:
        return {
            "schema": [
                {"name": f.name, "type": f.type_name, "primary": f.primary} for f in self.fields
            ],
            "indexes": sorted([f for f in self.indexed_fields if f != self.pk_field]),
        }

    def load_rows(self, rows: list[dict[str, Any]]) -> None:
        self.rows = {}
        self.pk_index = AVLTree()
        self.secondary_indexes = {
            f: AVLTree() for f in self.indexed_fields if f != self.pk_field
        }
        for row in rows:
            coerced = self._coerce_record(row)
            pk = coerced[self.pk_field]
            self.rows[pk] = coerced
            self.pk_index.insert(pk, pk)
            self._add_to_secondary_indexes(pk, coerced)

    def _coerce_value(self, field_name: str, value: Any) -> Any:
        f = self.field_map[field_name]
        t = f.type_name
        if t == "int":
            if isinstance(value, bool):
                raise ValueError(f"{field_name} espera entero")
            return int(value)
        if t == "real":
            if isinstance(value, bool):
                raise ValueError(f"{field_name} espera real")
            return float(value)
        if t == "bool":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                low = value.lower()
                if low in ("true", "1"):
                    return True
                if low in ("false", "0"):
                    return False
            raise ValueError(f"{field_name} espera boolean")
        return str(value)

    def _coerce_record(self, record: dict[str, Any]) -> dict[str, Any]:
        field_names = set(self.field_map.keys())
        record_names = set(record.keys())
        if field_names != record_names:
            missing = field_names - record_names
            extra = record_names - field_names
            raise ValueError(f"Columnas invalidas. Faltan={sorted(missing)} Sobran={sorted(extra)}")
        return {k: self._coerce_value(k, record[k]) for k in self.field_map}

    def _add_to_secondary_indexes(self, pk: Any, row: dict[str, Any]) -> None:
        for field, tree in self.secondary_indexes.items():
            key = row[field]
            bucket = tree.get(key)
            if bucket is None:
                tree.insert(key, {pk})
            else:
                bucket.add(pk)

    def _remove_from_secondary_indexes(self, pk: Any, row: dict[str, Any]) -> None:
        for field, tree in self.secondary_indexes.items():
            key = row[field]
            bucket = tree.get(key)
            if bucket is None:
                continue
            bucket.discard(pk)
            if not bucket:
                tree.delete(key)

    def insert(self, record: dict[str, Any]) -> None:
        coerced = self._coerce_record(record)
        pk = coerced[self.pk_field]
        if self.pk_index.contains(pk):
            raise ValueError(f"Clave primaria duplicada: {pk}")
        self.rows[pk] = coerced
        self.pk_index.insert(pk, pk)
        self._add_to_secondary_indexes(pk, coerced)

    def _match(self, row: dict[str, Any], condition: Condition | None) -> bool:
        if condition is None:
            return True
        val = row.get(condition.field)
        if condition.op == "eq":
            return val == condition.value
        if condition.op == "gt":
            return val > condition.value
        if condition.op == "lt":
            return val < condition.value
        if condition.op == "gte":
            return val >= condition.value
        if condition.op == "lte":
            return val <= condition.value
        if condition.op == "between":
            return condition.value <= val <= condition.second_value
        return False

    def _candidate_pks(self, condition: Condition | None) -> list[Any]:
        if condition is None:
            return [pk for _, pk in self.pk_index.inorder()]

        field = condition.field
        if field == self.pk_field and condition.op == "eq":
            pk = self.pk_index.get(condition.value)
            return [] if pk is None else [pk]

        if field == self.pk_field and condition.op == "between":
            return [pk for _, pk in self.pk_index.inorder(condition.value, condition.second_value)]

        if field == self.pk_field and condition.op in {"gt", "gte", "lt", "lte"}:
            if condition.op == "gt":
                return [pk for _, pk in self.pk_index.inorder(condition.value, None) if pk > condition.value]
            if condition.op == "gte":
                return [pk for _, pk in self.pk_index.inorder(condition.value, None)]
            if condition.op == "lt":
                return [pk for _, pk in self.pk_index.inorder(None, condition.value) if pk < condition.value]
            return [pk for _, pk in self.pk_index.inorder(None, condition.value)]

        if field in self.secondary_indexes:
            tree = self.secondary_indexes[field]
            if condition.op == "eq":
                bucket = tree.get(condition.value)
                return sorted(bucket) if bucket else []
            if condition.op == "between":
                out: set[Any] = set()
                for _, bucket in tree.inorder(condition.value, condition.second_value):
                    out.update(bucket)
                return sorted(out)
            if condition.op in {"gt", "gte", "lt", "lte"}:
                out: set[Any] = set()
                if condition.op == "gt":
                    for key, bucket in tree.inorder(condition.value, None):
                        if key > condition.value:
                            out.update(bucket)
                elif condition.op == "gte":
                    for _, bucket in tree.inorder(condition.value, None):
                        out.update(bucket)
                elif condition.op == "lt":
                    for key, bucket in tree.inorder(None, condition.value):
                        if key < condition.value:
                            out.update(bucket)
                else:
                    for _, bucket in tree.inorder(None, condition.value):
                        out.update(bucket)
                return sorted(out)

        return [pk for pk, row in self.rows.items() if self._match(row, condition)]

    def find(self, condition: Condition | None = None) -> list[dict[str, Any]]:
        result = []
        for pk in self._candidate_pks(condition):
            row = self.rows.get(pk)
            if row and self._match(row, condition):
                result.append(dict(row))
        return result

    def update(self, updates: dict[str, Any], condition: Condition | None = None) -> int:
        if self.pk_field in updates:
            raise ValueError("No se permite actualizar la clave primaria")

        for field in updates:
            if field not in self.field_map:
                raise ValueError(f"Campo no existe: {field}")

        targets = self._candidate_pks(condition)
        count = 0
        for pk in targets:
            row = self.rows.get(pk)
            if not row or not self._match(row, condition):
                continue

            old_row = dict(row)
            for field, raw_val in updates.items():
                row[field] = self._coerce_value(field, raw_val)

            self._remove_from_secondary_indexes(pk, old_row)
            self._add_to_secondary_indexes(pk, row)
            count += 1

        return count

    def delete(self, condition: Condition | None = None) -> int:
        targets = self._candidate_pks(condition)
        count = 0
        for pk in targets:
            row = self.rows.get(pk)
            if not row or not self._match(row, condition):
                continue
            self._remove_from_secondary_indexes(pk, row)
            self.pk_index.delete(pk)
            del self.rows[pk]
            count += 1
        return count

    def export_rows(self) -> list[dict[str, Any]]:
        return self.find(None)


class DatabaseEngine:
    def __init__(self, data_dir: str = "./data") -> None:
        self.storage = StorageManager(data_dir)
        self.tables: dict[str, Table] = {}
        self._load()

    def _load(self) -> None:
        catalog = self.storage.load_catalog()
        for table_name, meta in catalog.get("tables", {}).items():
            fields = [
                Field(name=f["name"], type_name=f["type"], primary=f.get("primary", False))
                for f in meta["schema"]
            ]
            table = Table(table_name, fields, indexed_fields=meta.get("indexes", []))
            rows = self.storage.load_table_rows(table_name)
            table.load_rows(rows)
            self.tables[table_name] = table

    def _save_catalog(self) -> None:
        catalog = {"tables": {name: table.to_metadata() for name, table in self.tables.items()}}
        self.storage.save_catalog(catalog)

    def _save_table(self, table_name: str) -> None:
        table = self.tables[table_name]
        self.storage.save_table_rows(table_name, table.export_rows())

    def create_table(self, table_name: str, columns: list[tuple[str, str, bool]]) -> None:
        if table_name in self.tables:
            raise ValueError(f"La tabla ya existe: {table_name}")
        fields = [Field(name=n, type_name=t, primary=p) for n, t, p in columns]
        primary_count = sum(1 for f in fields if f.primary)
        if primary_count == 0:
            fields[0].primary = True
        elif primary_count > 1:
            raise ValueError("Solo se permite una clave primaria")

        table = Table(table_name, fields)
        self.tables[table_name] = table
        self._save_catalog()
        self._save_table(table_name)

    def drop_table(self, table_name: str) -> None:
        if table_name not in self.tables:
            raise ValueError(f"Tabla no existe: {table_name}")
        del self.tables[table_name]
        self.storage.delete_table(table_name)
        self._save_catalog()

    def create_index(self, table_name: str, field_name: str) -> None:
        table = self._get_table(table_name)
        if field_name not in table.field_map:
            raise ValueError(f"Campo no existe: {field_name}")
        if field_name == table.pk_field:
            return
        if field_name in table.indexed_fields:
            return

        table.indexed_fields.add(field_name)
        tree = AVLTree()
        for pk, row in table.rows.items():
            key = row[field_name]
            bucket = tree.get(key)
            if bucket is None:
                tree.insert(key, {pk})
            else:
                bucket.add(pk)
        table.secondary_indexes[field_name] = tree

        self._save_catalog()

    def insert(self, table_name: str, values: dict[str, Any]) -> None:
        table = self._get_table(table_name)
        table.insert(values)
        self._save_table(table_name)

    def select(
        self,
        table_name: str,
        condition: Condition | None = None,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        table = self._get_table(table_name)
        rows = table.find(condition)
        if columns is None:
            return rows

        for col in columns:
            if col not in table.field_map:
                raise ValueError(f"Campo no existe en SELECT: {col}")

        projected: list[dict[str, Any]] = []
        for row in rows:
            projected.append({col: row[col] for col in columns})
        return projected

    def update(self, table_name: str, updates: dict[str, Any], condition: Condition | None = None) -> int:
        table = self._get_table(table_name)
        count = table.update(updates, condition)
        self._save_table(table_name)
        return count

    def delete(self, table_name: str, condition: Condition | None = None) -> int:
        table = self._get_table(table_name)
        count = table.delete(condition)
        self._save_table(table_name)
        return count

    def _get_table(self, table_name: str) -> Table:
        table = self.tables.get(table_name)
        if table is None:
            raise ValueError(f"Tabla no existe: {table_name}")
        return table

    def execute(self, sql: str) -> Any:
        cmd = sql.strip().rstrip(";")
        if not cmd:
            return ""

        up = cmd.upper()

        if up.startswith("CREATE TABLE"):
            return self._exec_create_table(cmd)
        if up.startswith("DROP TABLE"):
            return self._exec_drop_table(cmd)
        if up.startswith("CREATE INDEX"):
            return self._exec_create_index(cmd)
        if up.startswith("INSERT INTO"):
            return self._exec_insert(cmd)
        if up.startswith("SELECT"):
            return self._exec_select(cmd)
        if up.startswith("UPDATE"):
            return self._exec_update(cmd)
        if up.startswith("DELETE FROM"):
            return self._exec_delete(cmd)

        raise ValueError("Comando no soportado")

    def _exec_create_table(self, cmd: str) -> str:
        import re

        m = re.fullmatch(r"CREATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.+)\)", cmd, flags=re.IGNORECASE)
        if not m:
            raise ValueError("Sintaxis CREATE TABLE invalida")

        table_name = m.group(1)
        raw_columns = split_csv(m.group(2))
        columns: list[tuple[str, str, bool]] = []

        for col in raw_columns:
            cm = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)\s+(INT|INTEGER|TEXT|REAL|BOOL|BOOLEAN)(\s+PRIMARY\s+KEY)?",
                col,
                flags=re.IGNORECASE,
            )
            if not cm:
                raise ValueError(f"Definicion de columna invalida: {col}")
            name = cm.group(1)
            type_name = TYPE_ALIASES[cm.group(2).lower()]
            primary = cm.group(3) is not None
            columns.append((name, type_name, primary))

        self.create_table(table_name, columns)
        return f"Tabla creada: {table_name}"

    def _exec_drop_table(self, cmd: str) -> str:
        import re

        m = re.fullmatch(r"DROP\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)", cmd, flags=re.IGNORECASE)
        if not m:
            raise ValueError("Sintaxis DROP TABLE invalida")
        table_name = m.group(1)
        self.drop_table(table_name)
        return f"Tabla borrada: {table_name}"

    def _exec_create_index(self, cmd: str) -> str:
        import re

        m = re.fullmatch(
            r"CREATE\s+INDEX\s+([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([A-Za-z_][A-Za-z0-9_]*)\)",
            cmd,
            flags=re.IGNORECASE,
        )
        if not m:
            raise ValueError("Sintaxis CREATE INDEX invalida")

        idx_name, table_name, field = m.group(1), m.group(2), m.group(3)
        self.create_index(table_name, field)
        return f"Indice creado: {idx_name}"

    def _exec_insert(self, cmd: str) -> str:
        import re

        m = re.fullmatch(
            r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.+)\)\s*VALUES\s*\((.+)\)",
            cmd,
            flags=re.IGNORECASE,
        )
        if not m:
            raise ValueError("Sintaxis INSERT invalida")

        table_name = m.group(1)
        fields = split_csv(m.group(2))
        values = split_csv(m.group(3))
        if len(fields) != len(values):
            raise ValueError("Cantidad de columnas y valores no coincide")

        row = {f.strip(): parse_value(v) for f, v in zip(fields, values)}
        self.insert(table_name, row)
        return "1 fila insertada"

    def _exec_select(self, cmd: str) -> list[dict[str, Any]]:
        import re

        m = re.fullmatch(
            r"SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+WHERE\s+(.+))?",
            cmd,
            flags=re.IGNORECASE,
        )
        if not m:
            raise ValueError("Sintaxis SELECT invalida")

        raw_cols = m.group(1).strip()
        table_name = m.group(2)
        cond = parse_condition(m.group(3))

        columns: list[str] | None
        if raw_cols == "*":
            columns = None
        else:
            columns = [c.strip() for c in split_csv(raw_cols)]
            if not columns:
                raise ValueError("Debe indicar al menos una columna en SELECT")

        return self.select(table_name, cond, columns)

    def _exec_update(self, cmd: str) -> str:
        import re

        m = re.fullmatch(
            r"UPDATE\s+([A-Za-z_][A-Za-z0-9_]*)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?",
            cmd,
            flags=re.IGNORECASE,
        )
        if not m:
            raise ValueError("Sintaxis UPDATE invalida")

        table_name = m.group(1)
        assigns = split_csv(m.group(2))
        updates: dict[str, Any] = {}
        for assign in assigns:
            am = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", assign.strip())
            if not am:
                raise ValueError(f"Asignacion invalida: {assign}")
            updates[am.group(1)] = parse_value(am.group(2))

        cond = parse_condition(m.group(3))
        count = self.update(table_name, updates, cond)
        return f"{count} filas actualizadas"

    def _exec_delete(self, cmd: str) -> str:
        import re

        m = re.fullmatch(
            r"DELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+WHERE\s+(.+))?",
            cmd,
            flags=re.IGNORECASE,
        )
        if not m:
            raise ValueError("Sintaxis DELETE invalida")

        table_name = m.group(1)
        cond = parse_condition(m.group(2))
        count = self.delete(table_name, cond)
        return f"{count} filas borradas"


def default_data_dir() -> str:
    return str(Path(__file__).resolve().parent.parent / "data")
