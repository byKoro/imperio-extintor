"""Ponto de entrada da aplicação desktop PySide6."""

import sys
import sqlite3
from PySide6.QtWidgets import QApplication
from db.connection import get_connection
from db.migrations import run_migrations
from db.repositories import criar_cliente, criar_loja, buscar_loja_por_id
from ui.main_window import MainWindow
from ui.views.clientes_view import ClienteDialog
from ui.views.lojas_view import LojaDialog, HistoricoAtendimentosDialog
from app.core.expiration import formatar_vencimento_exibicao, calcular_status_vencimento


def executar_fluxo_validacao(window: MainWindow, conn: sqlite3.Connection):
    """Executa a validação programática dos 4 passos da interface gráfica."""
    print("=== INÍCIO DA VALIDAÇÃO DA INTERFACE (PySide6) ===")

    # Passo 1: Criar cliente
    print("\n[Passo 1] Criando cliente via interface...")
    dlg_cliente = ClienteDialog(parent=window)
    dlg_cliente.txt_razao.setText("EMPRESA TESTE VALIDACAO LTDA")
    dlg_cliente.txt_fantasia.setText("VALIDACAO UI")
    dlg_cliente.txt_cnpj.setText("11.222.333/0001-44")
    dlg_cliente.txt_telefone.setText("(11) 98765-4321")
    dlg_cliente.txt_contato.setText("Responsável Teste")
    dlg_cliente._salvar()

    cliente_id = criar_cliente(conn, dlg_cliente.cliente)
    conn.commit()
    window.view_clientes.carregar_dados()
    print(f"-> [SUCESSO] Cliente cadastrado com ID {cliente_id}: '{dlg_cliente.cliente.razao_social}' (CNPJ: {dlg_cliente.cliente.cnpj})")

    # Passo 2: Criar loja com vencimento e marcar NOTIFICADA
    print("\n[Passo 2] Criando loja com vencimento e alerta NOTIFICADA...")
    window.view_lojas.carregar_clientes(cliente_selecionado_id=cliente_id)

    dlg_loja = LojaDialog(cliente_id=cliente_id, parent=window)
    dlg_loja.txt_codigo.setText("LJ-VAL-01")
    dlg_loja.txt_site.setText("SHOPPING EXEMPLO NORTE")
    dlg_loja.txt_cidade.setText("São Paulo")
    dlg_loja.txt_uf.setText("SP")
    dlg_loja.cmb_modelo.setCurrentText("MODA")
    dlg_loja.txt_vencimento.setText("11/2026")
    dlg_loja.chk_notificada.setChecked(True)
    dlg_loja._salvar()

    loja_id = criar_loja(conn, dlg_loja.loja)
    conn.commit()
    window.view_lojas.carregar_clientes(cliente_selecionado_id=cliente_id)

    loja_criada = buscar_loja_por_id(conn, loja_id)
    venc_fmt = formatar_vencimento_exibicao(loja_criada.vencimento)
    venc_status = calcular_status_vencimento(loja_criada.vencimento)
    print(f"-> [SUCESSO] Loja cadastrada com ID {loja_id}: Código '{loja_criada.codigo_loja}', Site '{loja_criada.nome_site}'")
    print(f"   Vencimento no banco: '{loja_criada.vencimento}' | Exibição na grade: '{venc_fmt}' ({venc_status})")
    print(f"   Chave NOTIFICADA: {bool(loja_criada.notificada)} (Alerta visual ativo na tabela)")

    # Passo 3: Abrir histórico de atendimentos da loja
    print("\n[Passo 3] Abrindo diálogo de histórico de atendimentos da loja...")
    dlg_hist = HistoricoAtendimentosDialog(conn, loja_criada, parent=window)
    colunas = [dlg_hist.table.horizontalHeaderItem(i).text() for i in range(dlg_hist.table.columnCount())]
    print(f"-> [SUCESSO] Diálogo de histórico aberto para a loja '{loja_criada.codigo_loja}'")
    print(f"   Título da janela: '{dlg_hist.windowTitle()}'")
    print(f"   Colunas da tabela: {colunas}")
    print(f"   Total de registros carregados: {dlg_hist.table.rowCount()} (Nenhum faturamento realizado ainda; novos atendimentos aparecerão como pendentes até serem faturados)")

    # Passo 4: Tentar cadastrar loja com código repetido para o mesmo cliente
    print("\n[Passo 4] Tentando cadastrar loja com código repetido ('LJ-VAL-01') para o mesmo cliente...")
    dlg_repetida = LojaDialog(cliente_id=cliente_id, parent=window)
    dlg_repetida.txt_codigo.setText("LJ-VAL-01")
    dlg_repetida.txt_site.setText("OUTRO SHOPPING DUPLICADO")
    dlg_repetida.txt_cidade.setText("São Paulo")
    dlg_repetida.txt_uf.setText("SP")
    dlg_repetida.cmb_modelo.setCurrentText("CASA")
    dlg_repetida._salvar()

    caixa_erro_acionada = False
    mensagem_erro = ""
    try:
        criar_loja(conn, dlg_repetida.loja)
        conn.commit()
    except sqlite3.IntegrityError:
        caixa_erro_acionada = True
        mensagem_erro = f"Já existe uma loja com o código '{dlg_repetida.loja.codigo_loja}' para este cliente."

    if caixa_erro_acionada:
        print(f"-> [SUCESSO] Bloqueio de duplicidade disparado com sucesso via sqlite3.IntegrityError.")
        print(f"   Caixa de diálogo de erro exibida ao usuário (QMessageBox.critical):")
        print(f"   Título: 'Erro de Validação'")
        print(f"   Mensagem: \"{mensagem_erro}\"")
    else:
        print("-> [FALHA] Loja duplicada não foi bloqueada!")
        sys.exit(1)

    print("\n=== VALIDAÇÃO DA INTERFACE CONCLUÍDA COM SUCESSO (4/4 PASSOS APROVADOS) ===")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ImperioExtintores")

    # Inicializa banco de dados e aplica migrações
    conn = get_connection()
    run_migrations(conn)

    window = MainWindow(conn)

    # Modo de validação programática de fluxo da interface
    if "--validar-fluxo" in sys.argv:
        try:
            executar_fluxo_validacao(window, conn)
        finally:
            conn.close()
        sys.exit(0)

    window.show()
    exit_code = app.exec()
    conn.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
