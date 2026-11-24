# ==============================================================================
# PROYECTO: BARCODE-CREATOR | FIRMA: JOMOCE-SOFT
# LICENCIA: GNU GENERAL PUBLIC LICENSE V3 (GNU GPLv3)
# COPYRIGHT (C) 2026 JOMOCE-SOFT - TODOS LOS DERECHOS CONCEDIDOS BAJO GNU GPLv3
# ==============================================================================
import json
import sqlite3
from datetime import datetime
import pandas as pd
from rutas import obtener_dir_datos

RUTA_DB = obtener_dir_datos() / "barcode_creator.db"


def _conectar():
    conn = sqlite3.connect(str(RUTA_DB), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _esc_sql(identificador: str) -> str:
    """Escapa de forma segura un nombre de columna SQLite entre comillas dobles."""
    return '"' + str(identificador).replace('"', '""') + '"'


def inicializar_db():
    with _conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadatos_catalogo (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plantillas_etiquetas (
                nombre TEXT PRIMARY KEY,
                config_json TEXT NOT NULL
            )
        """)
        conn.commit()


def _tabla_catalogo_existe(conn) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='catalogo_productos'"
    )
    return cur.fetchone() is not None


def obtener_estado_catalogo() -> dict:
    inicializar_db()
    with _conectar() as conn:
        cur = conn.execute("SELECT clave, valor FROM metadatos_catalogo")
        meta = {r["clave"]: r["valor"] for r in cur.fetchall()}
    return {
        "ruta_db": str(RUTA_DB),
        "version": meta.get("VERSION_DB", "0"),
        "actualizado": meta.get("ULTIMA_ACTUALIZACION", "SIN REGISTROS"),
    }


def guardar_catalogo(df: pd.DataFrame, modo: str = "REEMPLAZAR"):
    """Elimina y recrea la tabla catalogo_productos a medida del Excel/CSV (o agrega columnas/filas)."""
    inicializar_db()
    df_limpio = df.copy()
    df_limpio.columns = [str(c).strip().upper() for c in df_limpio.columns]
    df_limpio = df_limpio.fillna("").apply(lambda col: col.astype(str).str.strip().str.upper())

    columnas_nuevas = list(df_limpio.columns)
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    with _conectar() as conn:
        if modo == "REEMPLAZAR" or not _tabla_catalogo_existe(conn):
            conn.execute("DROP TABLE IF EXISTS catalogo_productos")
            defs_cols = ['"__ID__" INTEGER PRIMARY KEY AUTOINCREMENT'] + [
                f"{_esc_sql(col)} TEXT NOT NULL DEFAULT ''" for col in columnas_nuevas
            ]
            conn.execute(f"CREATE TABLE catalogo_productos ({', '.join(defs_cols)})")
            columnas_finales = columnas_nuevas
        else:
            cur_info = conn.execute("PRAGMA table_info(catalogo_productos)")
            cols_actuales = [r["name"] for r in cur_info.fetchall() if r["name"] != "__ID__"]
            for col in columnas_nuevas:
                if col not in cols_actuales:
                    conn.execute(
                        f"ALTER TABLE catalogo_productos ADD COLUMN {_esc_sql(col)} TEXT NOT NULL DEFAULT ''"
                    )
                    cols_actuales.append(col)
            columnas_finales = cols_actuales

        # INSERTAR REGISTROS EN LA TABLA A MEDIDA
        cols_sql = ", ".join(_esc_sql(c) for c in columnas_nuevas)
        placeholders = ", ".join("?" for _ in columnas_nuevas)
        filas_valores = [tuple(fila) for fila in df_limpio[columnas_nuevas].itertuples(index=False, name=None)]

        conn.executemany(
            f"INSERT INTO catalogo_productos ({cols_sql}) VALUES ({placeholders})",
            filas_valores,
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadatos_catalogo (clave, valor) VALUES ('COLUMNAS', ?)",
            (json.dumps(columnas_finales, ensure_ascii=False),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadatos_catalogo (clave, valor) VALUES ('VERSION_DB', ?)",
            (marca_tiempo,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadatos_catalogo (clave, valor) VALUES ('ULTIMA_ACTUALIZACION', ?)",
            (marca_tiempo[:19],),
        )
        conn.commit()


def cargar_catalogo() -> pd.DataFrame:
    inicializar_db()
    with _conectar() as conn:
        if not _tabla_catalogo_existe(conn):
            return pd.DataFrame()

        cur_info = conn.execute("PRAGMA table_info(catalogo_productos)")
        columnas = [r["name"] for r in cur_info.fetchall() if r["name"] != "__ID__"]
        if not columnas:
            return pd.DataFrame()

        cols_sql = ", ".join(_esc_sql(c) for c in columnas)
        cur_rows = conn.execute(f"SELECT {cols_sql} FROM catalogo_productos ORDER BY \"__ID__\" ASC")
        filas = [tuple(r) for r in cur_rows.fetchall()]

    if not filas:
        return pd.DataFrame(columns=columnas)

    df = pd.DataFrame(filas, columns=columnas)
    return df.fillna("").apply(lambda c: c.astype(str).str.strip().str.upper())


def limpiar_catalogo():
    """Elimina por completo la tabla catalogo_productos, metadatos y compacta la base de datos."""
    inicializar_db()
    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    with _conectar() as conn:
        conn.execute("DROP TABLE IF EXISTS catalogo_productos")
        conn.execute("DELETE FROM metadatos_catalogo")
        conn.execute(
            "INSERT OR REPLACE INTO metadatos_catalogo (clave, valor) VALUES ('VERSION_DB', ?)",
            (marca_tiempo,),
        )
        conn.commit()
    with _conectar() as conn:
        conn.execute("VACUUM")


def guardar_plantilla(nombre: str, config: dict):
    inicializar_db()
    nombre_upper = str(nombre).strip().upper()
    if not nombre_upper:
        raise ValueError("EL NOMBRE DE LA PLANTILLA NO PUEDE ESTAR VACIO.")
    with _conectar() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO plantillas_etiquetas (nombre, config_json) VALUES (?, ?)",
            (nombre_upper, json.dumps(config, ensure_ascii=False)),
        )
        conn.commit()


def listar_plantillas() -> dict:
    inicializar_db()
    with _conectar() as conn:
        cur = conn.execute("SELECT nombre, config_json FROM plantillas_etiquetas ORDER BY nombre ASC")
        return {r["nombre"]: json.loads(r["config_json"]) for r in cur.fetchall()}


def eliminar_plantilla(nombre: str):
    inicializar_db()
    with _conectar() as conn:
        conn.execute("DELETE FROM plantillas_etiquetas WHERE nombre = ?", (str(nombre).strip().upper(),))
        conn.commit()

