from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .engine import DatabaseEngine


class MiniDBGUi:
    def __init__(self, root: tk.Tk, data_dir: str) -> None:
        self.root = root
        self.root.title("MiniDB AVL - Aplicacion de Escritorio")
        self.root.geometry("1120x700")
        self.root.minsize(980, 620)

        self.engine = DatabaseEngine(data_dir)
        self.current_rows: list[dict[str, object]] = []

        self._configure_style()
        self._build_layout()
        self.refresh_table_list()
        self.set_status("Listo")

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", foreground="#555")

    def _build_layout(self) -> None:
        self._build_menu()

        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X)

        ttk.Label(header, text="MiniDB AVL", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="Gestor relacional con indices AVL",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=(12, 0))

        actions = ttk.Frame(header)
        actions.pack(side=tk.RIGHT)
        ttk.Button(actions, text="Refrescar", command=self.refresh_table_list).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cargar ejemplo", command=self.load_example).pack(side=tk.LEFT, padx=(8, 0))

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        console_tab = ttk.Frame(notebook, padding=10)
        explorer_tab = ttk.Frame(notebook, padding=10)
        notebook.add(console_tab, text="Consola SQL")
        notebook.add(explorer_tab, text="Explorador de Datos")

        self._build_console_tab(console_tab)
        self._build_explorer_tab(explorer_tab)

        self.status_var = tk.StringVar(value="")
        status = ttk.Label(container, textvariable=self.status_var, anchor=tk.W, style="Muted.TLabel")
        status.pack(fill=tk.X, pady=(8, 0))

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        app_menu = tk.Menu(menu, tearoff=False)
        app_menu.add_command(label="Refrescar tablas", command=self.refresh_table_list)
        app_menu.add_separator()
        app_menu.add_command(label="Salir", command=self.root.destroy)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="Comandos de ejemplo", command=self.load_example)

        menu.add_cascade(label="Aplicacion", menu=app_menu)
        menu.add_cascade(label="Ayuda", menu=help_menu)

    def _build_console_tab(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(top)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = ttk.Frame(top, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))

        ttk.Label(left, text="Comandos SQL-like").pack(anchor=tk.W)
        self.command_text = scrolledtext.ScrolledText(left, height=7, wrap=tk.WORD)
        self.command_text.pack(fill=tk.X, pady=(4, 8))

        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Ejecutar", command=self.execute_command).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Limpiar salida", command=self.clear_output).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Usar query rapida", command=self.use_selected_quick_query).pack(side=tk.LEFT)

        ttk.Label(left, text="Salida").pack(anchor=tk.W, pady=(10, 0))
        self.output_text = scrolledtext.ScrolledText(left, height=22, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Tablas detectadas").pack(anchor=tk.W)
        self.tables_list = tk.Listbox(right, height=12)
        self.tables_list.pack(fill=tk.X, pady=(4, 8))
        self.tables_list.bind("<<ListboxSelect>>", self.on_table_selected)

        ttk.Label(right, text="Consultas rapidas").pack(anchor=tk.W)
        queries = [
            "SELECT * FROM alumnos;",
            "SELECT nombre, promedio FROM alumnos WHERE promedio >= 8.0;",
            "SELECT * FROM alumnos WHERE promedio > 8.0;",
            "SELECT * FROM alumnos WHERE promedio <= 9.0;",
        ]
        self.quick_combo = ttk.Combobox(right, values=queries, state="readonly")
        self.quick_combo.pack(fill=tk.X, pady=(4, 8))

        hint = (
            "Sugerencia:\n"
            "1) Crear tabla\n"
            "2) Insertar datos\n"
            "3) Ejecutar SELECT/UPDATE/DELETE\n"
            "4) Ver resultados en Explorador"
        )
        ttk.Label(right, text=hint, justify=tk.LEFT, style="Muted.TLabel").pack(anchor=tk.W)

    def _build_explorer_tab(self, parent: ttk.Frame) -> None:
        filters = ttk.LabelFrame(parent, text="Consulta visual", padding=10)
        filters.pack(fill=tk.X)

        ttk.Label(filters, text="Tabla").grid(row=0, column=0, sticky=tk.W)
        self.table_combo = ttk.Combobox(filters, state="readonly")
        self.table_combo.grid(row=1, column=0, sticky=tk.EW, padx=(0, 10), pady=(4, 0))

        ttk.Label(filters, text="Columnas (ej: id, nombre o *)").grid(row=0, column=1, sticky=tk.W)
        self.columns_entry = ttk.Entry(filters)
        self.columns_entry.insert(0, "*")
        self.columns_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 10), pady=(4, 0))

        ttk.Label(filters, text="WHERE opcional (ej: edad >= 18)").grid(row=0, column=2, sticky=tk.W)
        self.where_entry = ttk.Entry(filters)
        self.where_entry.grid(row=1, column=2, sticky=tk.EW, padx=(0, 10), pady=(4, 0))

        ttk.Button(filters, text="Cargar datos", command=self.load_table_data).grid(
            row=1,
            column=3,
            sticky=tk.EW,
            pady=(4, 0),
        )

        filters.columnconfigure(0, weight=1)
        filters.columnconfigure(1, weight=2)
        filters.columnconfigure(2, weight=3)

        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.result_table = ttk.Treeview(table_frame, show="headings")
        self.result_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.result_table.yview)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_table.configure(yscrollcommand=y_scroll.set)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def on_table_selected(self, _event: object) -> None:
        selection = self.tables_list.curselection()
        if not selection:
            return
        table_name = self.tables_list.get(selection[0])
        self.table_combo.set(table_name)
        self.columns_entry.delete(0, tk.END)
        self.columns_entry.insert(0, "*")
        self.where_entry.delete(0, tk.END)

    def use_selected_quick_query(self) -> None:
        selected = self.quick_combo.get().strip()
        if not selected:
            messagebox.showinfo("MiniDB AVL", "Seleccione una consulta rapida.")
            return
        self.command_text.delete("1.0", tk.END)
        self.command_text.insert("1.0", selected)

    def refresh_table_list(self) -> None:
        tables = sorted(self.engine.tables.keys())

        self.tables_list.delete(0, tk.END)
        for name in tables:
            self.tables_list.insert(tk.END, name)

        self.table_combo["values"] = tables
        if tables and not self.table_combo.get():
            self.table_combo.set(tables[0])

    def clear_output(self) -> None:
        self.output_text.delete("1.0", tk.END)

    def load_example(self) -> None:
        sample = (
            "CREATE TABLE alumnos (id INT PRIMARY KEY, nombre TEXT, promedio REAL, activo BOOL);\n"
            "CREATE INDEX idx_promedio ON alumnos (promedio);\n"
            "INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (1, 'Ana', 9.1, true);\n"
            "INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (2, 'Luis', 7.4, false);\n"
            "SELECT nombre, promedio FROM alumnos WHERE promedio >= 8.0;"
        )
        self.command_text.delete("1.0", tk.END)
        self.command_text.insert("1.0", sample)
        self.set_status("Ejemplo cargado en consola SQL")

    def _append_output(self, text: str) -> None:
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def _build_select_sql(self, table: str, columns: str, where_clause: str) -> str:
        cols = columns.strip() or "*"
        sql = f"SELECT {cols} FROM {table}"
        if where_clause.strip():
            sql += f" WHERE {where_clause.strip()}"
        return sql

    def _render_rows_in_grid(self, rows: list[dict[str, object]]) -> None:
        self.result_table.delete(*self.result_table.get_children())

        if not rows:
            self.result_table["columns"] = []
            return

        columns = list(rows[0].keys())
        self.result_table["columns"] = columns

        for col in columns:
            self.result_table.heading(col, text=col)
            self.result_table.column(col, width=160, anchor=tk.W)

        for row in rows:
            values = [row.get(col, "") for col in columns]
            self.result_table.insert("", tk.END, values=values)

    def load_table_data(self) -> None:
        table = self.table_combo.get().strip()
        if not table:
            messagebox.showinfo("MiniDB AVL", "Seleccione una tabla.")
            return

        columns = self.columns_entry.get().strip() or "*"
        where_clause = self.where_entry.get().strip()

        sql = self._build_select_sql(table, columns, where_clause)
        try:
            rows = self.engine.execute(sql)
            if not isinstance(rows, list):
                raise ValueError("La consulta visual solo acepta SELECT")
            self.current_rows = rows
            self._render_rows_in_grid(rows)
            self.set_status(f"Explorador: {len(rows)} fila(s) cargadas")
        except Exception as exc:
            messagebox.showerror("Error en consulta", str(exc))
            self.set_status(f"Error en explorador: {exc}")

    def execute_command(self) -> None:
        raw = self.command_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showinfo("MiniDB AVL", "Escriba al menos un comando.")
            return

        commands = [line.strip() for line in raw.split(";") if line.strip()]
        ok_count = 0
        for command in commands:
            try:
                result = self.engine.execute(command)
                self._append_output(f"db> {command};")
                if isinstance(result, list):
                    self._append_output(json.dumps(result, ensure_ascii=True, indent=2))
                    self.current_rows = result
                    self._render_rows_in_grid(result)
                else:
                    self._append_output(str(result))
                ok_count += 1
            except Exception as exc:
                self._append_output(f"ERROR: {exc}")
                self.set_status(f"Error: {exc}")

        self._append_output("-" * 60)
        self.refresh_table_list()
        if ok_count:
            self.set_status(f"Ejecucion finalizada: {ok_count} comando(s) correcto(s)")


def run_gui(data_dir: str) -> None:
    root = tk.Tk()
    _app = MiniDBGUi(root, data_dir)
    root.mainloop()
