"""Ponto de entrada da aplicação desktop PySide6."""

import sys
from PySide6.QtWidgets import QApplication
from db.connection import get_connection
from db.migrations import run_migrations
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ImperioExtintores")

    # Inicializa banco de dados e aplica migrações
    conn = get_connection()
    run_migrations(conn)

    window = MainWindow(conn)
    window.show()

    exit_code = app.exec()
    conn.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
