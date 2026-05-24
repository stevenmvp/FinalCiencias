from __future__ import annotations

import argparse
import json

from dbms.engine import DatabaseEngine, default_data_dir
from dbms.gui import run_gui


def run_repl() -> None:
    engine = DatabaseEngine(default_data_dir())
    print("MiniDB AVL (relacional). Escriba HELP para ayuda, EXIT para salir.")

    while True:
        try:
            line = input("db> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if not line:
            continue

        upper = line.upper()
        if upper in {"EXIT", "QUIT"}:
            print("Saliendo...")
            break
        if upper == "HELP":
            print(
                "Comandos:\n"
                "  CREATE TABLE t (id INT PRIMARY KEY, nombre TEXT, edad INT)\n"
                "  CREATE INDEX idx_edad ON t (edad)\n"
                "  INSERT INTO t (id, nombre, edad) VALUES (1, 'Ana', 20)\n"
                "  SELECT * FROM t WHERE id = 1\n"
                "  SELECT nombre, edad FROM t WHERE edad >= 18\n"
                "  SELECT * FROM t WHERE edad BETWEEN 18 AND 30\n"
                "  SELECT * FROM t WHERE edad > 18\n"
                "  SELECT * FROM t WHERE edad < 30\n"
                "  UPDATE t SET edad = 21 WHERE id = 1\n"
                "  DELETE FROM t WHERE id = 1\n"
                "  DROP TABLE t"
            )
            continue

        try:
            result = engine.execute(line)
            if isinstance(result, list):
                print(json.dumps(result, ensure_ascii=True, indent=2))
            else:
                print(result)
        except Exception as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MiniDB AVL")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Inicia en modo consola (REPL)",
    )
    args = parser.parse_args()

    if args.cli:
        run_repl()
    else:
        run_gui(default_data_dir())
