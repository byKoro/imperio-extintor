# To-do — Sistema de faturamento de manutenção de extintores

Referência principal das regras: `regras_negocio_faturamento.md`. Em caso de dúvida, a regra escrita nesse documento vence.

## Stack

- Python 3.12
- PySide6 (interface, tabelas em `QTableView` com filtro e ordenação)
- SQLite (banco local, arquivo único)
- openpyxl (leitura das planilhas atuais e exportação para .xlsx)
- ReportLab (geração dos PDFs)
- pytest (testes das regras de cálculo e importação)

## Regras que não podem ser quebradas

- Preço do item é copiado do produto no momento do lançamento. Alterar a tabela não mexe em pedidos existentes.
- Preço do produto vem da tabela por padrão, mas pode ser alterado por pedido.
- Total do pedido = soma dos itens. O valor impresso é o valor cobrado. Nenhum ajuste automático.
- Anotações manuais de papel não entram no cálculo. Observações são texto livre.
- Pedido faturado não pode ser editado.
- Ajuste (faturamento complementar) é sempre vinculado a um pedido executado. Não altera o pedido original.
- Cada ajuste é faturado uma única vez.
- NF não existe no sistema nesta etapa.
- Número do pedido é digitado, único por cliente.
- Status de vencimento é calculado pela data atual, nunca digitado.
- NOTIFICADA é só uma chave de alerta marcável. Não bloqueia nada.
- FINALIZADA, FECHADO e 4° REMESSA do histórico não são convertidos automaticamente para Faturado.
- Loja só é considerada atendida depois que o atendimento é faturado.

## Fase 1 — Base

- [x] Estrutura de pastas: `app/`, `db/`, `importers/`, `exporters/`, `pdf/`, `ui/`, `tests/`
- [x] Conexão SQLite e criação do schema
- [x] Migrações simples (script versionado)
- [x] Modelos: Cliente, Loja, Produto, Pedido, ItemPedido, Ajuste, Faturamento
- [x] Campos de Loja: ID (único por cliente), site, cidade, UF, modelo/bandeira (lista padronizada), vencimento, observação, chave NOTIFICADA
- [x] Lista padronizada de modelo/bandeira: MODA, CASA, CARTERS, FAN LAB, CD, MATRIZ, CCR e combinações
- [x] Campos de Cliente: razão social, nome fantasia, CNPJ, IE, endereço, telefone, e-mail, contato, condições comerciais padrão
- [x] Condições padrão do cliente: prazo de pagamento, forma de pagamento, prazo de entrega, texto de impostos
- [x] Testes das regras de cálculo (totais, preço copiado, ajuste)

## Fase 2 — Cadastros

- [x] Tela de clientes (CRUD)
- [x] Tela de lojas por cliente (CRUD) com histórico de atendimentos
- [x] Tela de produtos (CRUD): nome único, categoria, tipo (serviço ou peça), unidade (SV ou UN), capacidade, preço padrão
- [x] Tabela de preço por cliente (opcional): substitui o preço padrão só para os produtos que ela contém
- [x] Validação: nome de produto único, código de loja único dentro do cliente
- [ ] Reativar cadastro inativo pela tela de clientes e lojas (ver regras, seção 3.2)

## Fase 3 — Pedidos

- [x] Tela de pedido: número digitado (único por cliente), data de emissão, data de execução, cliente, loja
- [x] Seção Serviços e seção Peças separadas, com subtotais e total geral
- [x] Preço sugerido da tabela, editável no item
- [x] Itens avulsos com descrição livre e preço informado (não criam produto)
- [x] Observação em texto livre, sem efeito no cálculo
- [x] Condições do pedido vindas do cliente, editáveis no pedido
- [x] Status: Aberto → Executado (exige data de execução) → Faturado → Pago (opcional)
- [x] Marcação manual de Faturado em qualquer pedido Executado
- [x] Ação "duplicar pedido": nova cópia com quantidades e preços zerados, sem alterar o original
- [x] Pedido faturado bloqueado para edição

## Fase 4 — Ajustes (faturamento complementar)

- [ ] Criar ajuste vinculado a um pedido executado
- [ ] Ajuste registra apenas os itens acrescentados
- [ ] Modo "somente a diferença": PDF lista só os itens acrescentados
- [ ] Modo "valores incrementados": PDF mostra o pedido completo com quantidade original, acrescentada, final e totais
- [ ] Histórico no pedido: valor original faturado, cada ajuste e total acumulado
- [ ] Numeração do ajuste: confirmar formato antes de implementar (ex.: 20251954-A1)
- [ ] Ajuste faturado uma única vez

## Fase 5 — Faturamento mensal

- [ ] Gerar faturamento de um cliente por período (mês)
- [ ] Incluir pedidos Executados não faturados e ajustes pendentes
- [ ] Um pedido só pode estar em um faturamento
- [ ] Ao fechar o faturamento, os pedidos passam para Faturado
- [ ] Total por pedido e total geral do período

## Fase 6 — Vencimento e alertas

- [x] Status VENCIDO / NA VALIDADE calculado pela data atual
- [x] Destaque visual de vencidos na tela
- [x] Exibir chave NOTIFICADA como alerta na tela
- [ ] PESAGEM: pendente de definição, não implementar até confirmar a regra

## Fase 7 — Visualização em grade

- [ ] Grade em todas as listagens: lojas, produtos, pedidos, itens, faturamentos, histórico
- [ ] Ordenação por coluna
- [ ] Filtro por qualquer coluna (incluindo status, cliente, bandeira e UF)
- [ ] Busca por texto
- [ ] Escolha de colunas visíveis
- [ ] Exportar para .xlsx respeitando filtros e ordenação atuais
- [ ] Exportar para .csv respeitando filtros e ordenação atuais

## Fase 8 — Importação das planilhas

- [ ] Importar planilha de manutenções mensais (uma aba por mês)
- [ ] Ignorar linhas de subtotal (`=SUBTOTAL(...)`) e linhas sem ID
- [ ] Padronizar grafias de modelo/bandeira (ex.: FAN LAB e FANLAB)
- [ ] Tratar a coluna "DATA DE ATENDIMENTO": ela traz nome do mês ou status, não data. Guardar o valor original para conferência
- [ ] Importar planilha de controle de produtos e entregas (aba PRODUTOS e BASE TROCA)
- [ ] Relatório de importação: linhas importadas, ignoradas e com erro, antes de salvar
- [ ] Importação não sobrescreve registros existentes sem confirmação
- [ ] Testes com a planilha real da Riachuelo

## Fase 9 — PDFs

- [ ] PDF do pedido: cabeçalho do emitente, dados do cliente, número, datas, seções Serviços e Peças com subtotais, total geral, condições, observações, campos de aceite e autorização
- [ ] PDF do faturamento: cabeçalho, dados do cliente, período, lista de pedidos com número, data, loja e total, total geral
- [ ] PDF do ajuste nos dois modos
- [ ] Pré-visualização antes de gerar o arquivo final
- [ ] Dados do emitente em configuração, não fixos no código

## Fase 10 — Finalização

- [ ] Backup do banco (cópia manual ou automática ao fechar)
- [ ] Mensagens de erro claras para o usuário
- [ ] Testes de ponta a ponta: cadastro → pedido → executado → ajuste → faturamento → PDF → exportação
- [ ] Empacotamento para Windows com PyInstaller, gerado em máquina Windows (não há cross-compile)
- [ ] Escolher o modo de build: `--onedir` (recomendado para equipe pequena) ou `--onefile`
- [ ] Testar o `.exe` em uma máquina Windows limpa, sem Python instalado
- [ ] Incluir no pacote: modelos de PDF, logo da empresa e fontes usadas pelo ReportLab
- [ ] Dados e configurações em `%APPDATA%\ImperioExtintor\`, fora da pasta do programa
- [ ] Verificar que atualizar o `.exe` não apaga o banco nem as configurações
- [ ] Verificar bloqueio do Windows Defender e do antivírus da empresa; liberar o arquivo se necessário
- [ ] Avaliar assinatura de código para o `.exe` (reduz bloqueios, tem custo)
- [ ] Procedimento de atualização manual documentado: substituir a pasta do programa e manter a pasta de dados
- [ ] Documento de uso curto para a equipe

## Pendências (não implementar até confirmar)

- [ ] Regra da PESAGEM
- [ ] Significado de NOTIFICADA como bloqueio ou só informativo
- [ ] Significado de FINALIZADA, FECHADO e 4° REMESSA
- [ ] Numeração dos ajustes
- [ ] Ajuste negativo (divergência para menos): sim ou não
- [ ] Valor a cobrar no modo "valores incrementados": confirmar que é a diferença entre total final e o já faturado
- [ ] Se o faturamento precisa de totais por produto além dos totais por pedido
