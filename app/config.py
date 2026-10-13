"""Configurações gerais do sistema e caminhos de arquivos."""

import os
from pathlib import Path


APP_NAME = "ImperioExtintores"
ORG_NAME = "Imperio"


def get_app_data_dir() -> Path:
    """Retorna o diretório de dados em %APPDATA%/ImperioExtintor."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        base_dir = Path(appdata) / "ImperioExtintor"
    else:
        base_dir = Path.home() / ".imperio_extintores"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_default_db_path() -> Path:
    """Retorna o caminho padrão do banco de dados SQLite."""
    # Permite sobrescrever via variável de ambiente (ex.: para testes)
    env_db = os.environ.get("IMPERIO_DB_PATH")
    if env_db:
        return Path(env_db)

    # Em ambiente de desenvolvimento local, pode usar banco na pasta do projeto se existir
    local_db = Path(__file__).resolve().parent.parent / "imperio_faturamento.db"
    if local_db.exists():
        return local_db

    # Caminho de produção no AppData
    return get_app_data_dir() / "imperio_faturamento.db"
