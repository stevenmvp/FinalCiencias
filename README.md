# Motor/Gestor de Base de Datos Relacional con AVL

Implementacion de un mini gestor relacional con indice AVL propio, inspirado en comandos estilo SQLite.

## Caracteristicas

- Gestion de esquemas:
  - `CREATE TABLE`
  - `DROP TABLE`
  - tipos: `INT`, `TEXT`, `REAL`, `BOOL`
- CRUD:
  - `INSERT`, `SELECT`, `UPDATE`, `DELETE`
  - `SELECT *` o `SELECT col1, col2`
  - filtros en `WHERE`: `=`, `>`, `<`, `>=`, `<=`, `BETWEEN ... AND ...`
- Indexacion con arbol AVL propio:
  - indice primario obligatorio
  - indices secundarios opcionales con `CREATE INDEX`
  - operaciones AVL: insercion, busqueda, eliminacion, recorrido inorder
- Persistencia:
  - datos y catalogo en JSON
  - reconstruccion de indices al iniciar
- Atomicidad basica por operacion:
  - escritura atomica con archivo temporal + `os.replace`

## Ejecucion

```bash
c:/python314/python.exe main.py
```

El comando anterior abre la aplicacion de escritorio (GUI) por defecto.

Para abrir modo consola (REPL):

```bash
c:/python314/python.exe main.py --cli
```

En la consola:

```sql
CREATE TABLE alumnos (id INT PRIMARY KEY, nombre TEXT, promedio REAL, activo BOOL);
CREATE INDEX idx_promedio ON alumnos (promedio);
INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (1, 'Ana', 9.1, true);
SELECT * FROM alumnos WHERE promedio BETWEEN 8.0 AND 10.0;
SELECT nombre, promedio FROM alumnos WHERE promedio >= 8.5;
SELECT * FROM alumnos WHERE promedio > 8.0;
SELECT * FROM alumnos WHERE promedio <= 9.1;
UPDATE alumnos SET activo = false WHERE id = 1;
DELETE FROM alumnos WHERE id = 1;
DROP TABLE alumnos;
```

## Pruebas

```bash
c:/python314/python.exe -m unittest discover -s tests -v
```

## Funcionamiento Interno

### 1) Arquitectura general

- `main.py`: inicia un REPL (linea de comandos) y delega cada comando al motor.
- `dbms/engine.py`: contiene la logica del gestor relacional (tablas, indices, CRUD, parser SQL-like).
- `dbms/avl.py`: implementa el arbol AVL propio (sin librerias externas de AVL).
- `dbms/storage.py`: maneja persistencia en disco con escrituras atomicas.
- `dbms/parser.py`: parsea valores y condiciones de `WHERE`.

Flujo de una consulta:

1. El usuario escribe un comando en el REPL.
2. `DatabaseEngine.execute(...)` detecta el tipo de comando (`CREATE`, `INSERT`, `SELECT`, etc.).
3. El motor parsea la sentencia y llama a la operacion correspondiente.
4. La tabla usa su indice AVL (primario o secundario) para ubicar candidatos en `O(log n)`.
5. Se filtran/actualizan/eliminan filas y se persiste el estado en JSON.

### 2) Modelo relacional implementado

Cada tabla define:

- nombre de tabla
- esquema fijo: columnas con tipo (`INT`, `TEXT`, `REAL`, `BOOL`)
- una clave primaria (si no se especifica, se toma la primera columna)

Las filas se guardan internamente como diccionarios (columna -> valor), validados y convertidos a tipo antes de insertar/actualizar.

### 3) Indices AVL

- Indice primario:
  - siempre existe
  - mapea `pk -> pk` para busqueda/eliminacion eficientes
- Indices secundarios:
  - se crean con `CREATE INDEX ... ON tabla (campo)`
  - mapean `valor_campo -> set(pk)` para manejar valores repetidos

Operaciones AVL usadas:

- insercion (`insert`)
- busqueda (`get`)
- eliminacion (`delete`)
- recorrido inorder (`inorder`) para consultas de rango

### 4) Resolucion de WHERE

`WHERE` soporta:

- igualdad: `campo = valor`
- comparaciones: `campo > valor`, `campo < valor`, `campo >= valor`, `campo <= valor`
- rango: `campo BETWEEN a AND b`

Estrategia:

- Si el filtro es por clave primaria o por campo indexado, se usa AVL para obtener candidatos rapido.
- Si el campo no esta indexado, se aplica escaneo de filas y filtro en memoria.

### 5) SELECT por columnas

- `SELECT * FROM tabla ...` devuelve todas las columnas.
- `SELECT col1, col2 FROM tabla ...` proyecta solo columnas pedidas.
- Si una columna no existe, se lanza error de validacion.

### 6) Persistencia y restauracion

Archivos en `data/`:

- `catalog.json`: define tablas, esquema e indices.
- `tabla.json`: contiene filas de cada tabla.

Al iniciar:

1. Se carga el catalogo.
2. Se cargan filas por tabla.
3. Se reconstruyen indices AVL en memoria (rapido y determinista).

Atomicidad basica por operacion:

- Se escribe primero a `archivo.tmp`.
- Luego se reemplaza con `os.replace(tmp, destino)`.
- Si algo falla durante escritura, no se deja el archivo final corrupto.

## Como correr el programa paso a paso

1. Abrir terminal en la carpeta del proyecto.
2. Ejecutar:

```bash
c:/python314/python.exe main.py
```

Esto abre la interfaz de escritorio con pestañas Consola SQL y Explorador de Datos.

3. Probar este guion minimo:

```sql
CREATE TABLE alumnos (id INT PRIMARY KEY, nombre TEXT, promedio REAL, activo BOOL);
CREATE INDEX idx_promedio ON alumnos (promedio);
INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (1, 'Ana', 9.1, true);
INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (2, 'Luis', 7.4, false);
SELECT nombre, promedio FROM alumnos WHERE promedio >= 8.0;
UPDATE alumnos SET activo = false WHERE promedio > 8.0;
DELETE FROM alumnos WHERE promedio < 8.0;
SELECT * FROM alumnos;
```

4. Salir con `EXIT` o `QUIT`.

## Interfaz grafica (GUI)

La GUI esta implementada con `tkinter` (libreria estandar de Python, sin instalar paquetes extra).

### Como abrirla

```bash
c:/python314/python.exe main.py
```

### Que incluye la ventana

- area de entrada para escribir comandos SQL-like
- boton `Ejecutar` para correr uno o varios comandos
- salida en texto formateado (JSON para resultados de `SELECT`)
- lista de tablas detectadas en el motor
- consultas rapidas precargadas
- boton `Cargar ejemplo` para poblar un script de demostracion

### Como usarla

1. Abre la GUI con el comando principal (`main.py`).
2. Escribe un comando o varios separados por `;`.
3. Presiona `Ejecutar`.
4. Revisa la salida y la lista de tablas actualizada.

Ejemplo para pegar en la GUI:

```sql
CREATE TABLE alumnos (id INT PRIMARY KEY, nombre TEXT, promedio REAL, activo BOOL);
CREATE INDEX idx_promedio ON alumnos (promedio);
INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (1, 'Ana', 9.1, true);
INSERT INTO alumnos (id, nombre, promedio, activo) VALUES (2, 'Luis', 7.4, false);
SELECT nombre, promedio FROM alumnos WHERE promedio >= 8.0;
```

## Como correr pruebas

```bash
c:/python314/python.exe -m unittest discover -s tests -v
```

Las pruebas validan:

- CRUD completo
- consultas por igualdad y rango
- operadores `>`, `<`, `>=`, `<=`
- `SELECT` por columnas especificas
- persistencia y recarga de estado

## Complejidad

Suponiendo `n` registros y `k` resultados del rango.

- Insercion con indice AVL: `O(log n)` por indice
- Busqueda por clave primaria: `O(log n)`
- Busqueda por igualdad en campo indexado: `O(log n + m)` donde `m` es tamano del bucket
- Busqueda por rango en campo indexado: `O(log n + k)`
- Actualizacion/Borrado por clave primaria: `O(log n)`
- Recorrido inorder: `O(n)`

Espacio:

- Datos: `O(n)`
- Indices AVL: `O(n)`

## Limitaciones actuales

- No se permite actualizar la clave primaria.
- No hay `JOIN`, `ORDER BY`, `GROUP BY`, ni subconsultas.
- Se soportan filtros simples de un solo predicado en `WHERE`.
- Concurrencia no implementada (requisito opcional).
