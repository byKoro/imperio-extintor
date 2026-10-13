"""Mecanismo simples e versionado de migração do banco de dados SQLite."""

import sqlite3
from pathlib import Path
from typing import Dict, Callable

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _migration_v1(conn: sqlite3.Connection) -> None:
    """Migração inicial: aplica o schema.sql completo."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)


MIGRATIONS: Dict[int, tuple[str, Callable[[sqlite3.Connection], None]]] = {
    1: ("Criação inicial do schema (clientes, lojas, produtos, pedidos, faturamentos, ajustes)", _migration_v1),
}


def run_migrations(conn: sqlite3.Connection) -> int:
    """Executa todas as migrações pendentes em ordem crescente de versão.
    
    Retorna a versão atual do banco de dados após a execução.
    """
    cursor = conn.cursor()

    # Cria tabela de migrações se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            description TEXT
        )
    """)
    conn.commit()

    # Identifica a versão atual aplicada
    cursor.execute("SELECT MAX(version) FROM schema_migrations")
    row = cursor.fetchone()
    current_version = row[0] if (row and row[0] is not None) else 0

    # Aplica migrações pendentes
    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            desc, migration_func = MIGRATIONS[version]
            migration_func(conn)
            cursor.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, desc)
            )
            conn.commit()
            current_version = version

    return current_version
