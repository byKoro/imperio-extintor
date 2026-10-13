"""Gerenciador de conexão com o banco de dados SQLite."""

import sqlite3
from pathlib import Path
from typing import Union, Optional
from app.config import get_default_db_path


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Cria e retorna uma conexão configurada com o SQLite.
    
    Habilita foreign keys e define row_factory como sqlite3.Row.
    """
    if db_path is None:
        target = str(get_default_db_path())
    else:
        target = str(db_path)

    # Se for arquivo em disco, garante que o diretório pai exista
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
