from __future__ import annotations

import tempfile
import unittest

from dbms.engine import DatabaseEngine


class EngineTests(unittest.TestCase):
    def test_crud_with_indexes_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = DatabaseEngine(tmp)

            engine.execute("CREATE TABLE alumnos (id INT PRIMARY KEY, nombre TEXT, promedio REAL, activo BOOL)")
            engine.execute("CREATE INDEX idx_promedio ON alumnos (promedio)")

            engine.execute("INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (1, 'Ana', 9.1, true)")
            engine.execute("INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (2, 'Luis', 7.4, false)")
            engine.execute("INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (3, 'Marta', 8.2, true)")

            by_pk = engine.execute("SELECT * FROM alumnos WHERE id = 2")
            self.assertEqual(len(by_pk), 1)
            self.assertEqual(by_pk[0]["nombre"], "Luis")

            by_range = engine.execute("SELECT * FROM alumnos WHERE promedio BETWEEN 8.0 AND 9.5")
            self.assertEqual({r["id"] for r in by_range}, {1, 3})

            updated = engine.execute("UPDATE alumnos SET activo = false WHERE promedio BETWEEN 8.0 AND 9.5")
            self.assertIn("2", updated)

            remaining = engine.execute("DELETE FROM alumnos WHERE id = 2")
            self.assertIn("1", remaining)

            engine2 = DatabaseEngine(tmp)
            all_rows = engine2.execute("SELECT * FROM alumnos")
            self.assertEqual(len(all_rows), 2)
            self.assertEqual({r["id"] for r in all_rows}, {1, 3})

    def test_select_specific_columns_and_comparison_ops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = DatabaseEngine(tmp)

            engine.execute("CREATE TABLE productos (id INT PRIMARY KEY, nombre TEXT, precio REAL, stock INT)")
            engine.execute("CREATE INDEX idx_precio ON productos (precio)")

            engine.execute("INSERT INTO productos (id, nombre, precio, stock) VALUES (1, 'A', 10.0, 5)")
            engine.execute("INSERT INTO productos (id, nombre, precio, stock) VALUES (2, 'B', 15.0, 2)")
            engine.execute("INSERT INTO productos (id, nombre, precio, stock) VALUES (3, 'C', 20.0, 8)")

            cols = engine.execute("SELECT nombre, precio FROM productos WHERE precio >= 15.0")
            self.assertEqual(len(cols), 2)
            self.assertEqual(set(cols[0].keys()), {"nombre", "precio"})
            self.assertEqual(set(cols[1].keys()), {"nombre", "precio"})

            gt_rows = engine.execute("SELECT * FROM productos WHERE precio > 10.0")
            self.assertEqual({r["id"] for r in gt_rows}, {2, 3})

            lt_rows = engine.execute("SELECT * FROM productos WHERE precio < 20.0")
            self.assertEqual({r["id"] for r in lt_rows}, {1, 2})

            lte_rows = engine.execute("SELECT * FROM productos WHERE stock <= 5")
            self.assertEqual({r["id"] for r in lte_rows}, {1, 2})


if __name__ == "__main__":
    unittest.main()
