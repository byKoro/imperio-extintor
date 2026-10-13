# Regras de negócio — Sistema de faturamento de manutenção de extintores

Versão: 1.0 (rascunho validado nas respostas de 13/10/2026)

## 1. Escopo

- Sistema desktop em Python com interface gráfica.
- Substitui as planilhas de controle de pedidos, vencimentos e faturamento, mantendo a forma de trabalho atual da empresa.
- Gera o PDF do pedido e o PDF do faturamento mensal.
- Suporta múltiplos clientes. Hoje só há dados da Lojas Riachuelo S/A, mas a estrutura deve aceitar outros clientes sem alteração de código.
- Fora do escopo nesta etapa: emissão ou controle de Nota Fiscal (NF). O que hoje é anotado à mão continua sendo anotado à mão, e o sistema não substitui esse processo.

## 2. Entidades

- **Cliente**: razão social, nome fantasia, CNPJ, Inscrição Estadual, endereço, telefone, e-mail, contato e condições comerciais padrão.
- **Loja / unidade**: pertence a um cliente. Possui código/ID, nome do site, cidade, UF, base de atendimento e data de vencimento dos extintores.
- **Produto / serviço**: nome, categoria, tipo (serviço ou peça), unidade (SV ou UN), capacidade e preço padrão.
- **Pedido**: número, data de emissão, data de execução, cliente, loja, status, itens e observações.
- **Item do pedido**: produto, quantidade, preço unitário e total.
- **Faturamento mensal**: agrupa os pedidos executados de um cliente em um período.

## 3. Clientes e lojas

- Cada cliente tem seu próprio conjunto de lojas, condições comerciais e, opcionalmente, tabela de preços própria.
- Lojas são identificadas por código único dentro do cliente (ID).
- Campos da loja: ID, site, cidade, UF, modelo/bandeira (lista padronizada: MODA, CASA, CARTERS, FAN LAB, CD, MATRIZ, CCR e combinações), data de vencimento dos extintores, observação e uma chave de alerta "NOTIFICADA".
- A chave NOTIFICADA é marcada manualmente pelo usuário. Por ora, o sistema apenas exibe o alerta; o efeito dele sobre o faturamento ainda não está definido.
- Uma loja pode ser atendida mais de uma vez. Cada atendimento é um pedido, e o cadastro guarda o histórico de atendimentos.
- Uma loja só é considerada atendida depois que o atendimento é faturado. Atendimentos ainda não faturados aparecem como pendentes.
- Um pedido sempre pertence a um cliente e a uma loja.
- Cada unidade do cadastro tem: ID, nome do site (shopping ou local), modelo/bandeira, cidade, UF e observações fixas.
- O modelo/bandeira é um campo de lista controlada, com valores atuais: MODA, CASA, CARTERS, FAN LAB, MODA + CASA, MODA + CASA E CARTERS, MATRIZ, CD, CCR. Variações de digitação (ex.: "CARTERS " com espaço, "FAN LAB" e "FANLAB") devem ser normalizadas na importação.
- Um mesmo shopping pode ter várias unidades com IDs diferentes, uma por modelo (ex.: IBIRAPUERA SH CARTE´S e IBIRAPUERA SH CASA). Por isso a chave da unidade é o ID, não o nome do shopping.
- Observações fixas da loja, como "NOTIFICADA" e "ENCAIXE DE ROTEIRO", são campos de cadastro. O sistema deve listá-las na loja e também permitir registrá-las por atendimento, pois a planilha mostra que podem mudar de um mês para outro.

## 3.1 Histórico importado da planilha de manutenções

- A planilha de controle mensal (abas JANEIRO a DEZEMBRO, mais PRODUTOS) é a fonte de importação do histórico.
- Cada linha de uma aba mensal é um atendimento: ID da unidade, data de atendimento, observação e quantidades por produto.
- Os valores da planilha são calculados a partir da tabela de preços atual. Por isso o sistema deve gravar o preço no momento do lançamento. Se o preço da tabela mudar, o histórico importado não pode mudar junto.
- A planilha tem quantidades em colunas duplicadas para o mesmo produto (CO2 25 KG aparece em AD e AM; PQS BC 20 KG em Q e AQ; PQS BC 50 KG em S e AR). A importação deve unificar essas colunas no mesmo produto.
- A coluna "FATURADA?" está preenchida em apenas 5 das 458 linhas (SETEMBRO e OUTUBRO). Para as demais, o status de faturamento não está registrado, e a importação não deve assumir que estão faturadas ou não. Essa definição depende de confirmação.
- A aba mensal nem sempre coincide com a data de atendimento. Há linhas da aba MARÇO com atendimento em FEVEREIRO e ABRIL, por exemplo. O sistema precisa definir qual critério determina o período de faturamento.

## 3.2 Inativação e reativação de cadastros (clientes, lojas e produtos)

- Entidades cadastradas no sistema (**clientes**, **lojas** e **produtos**) que possuam qualquer vínculo com o histórico operacional ou financeiro não podem ser excluídas fisicamente do banco de dados, para garantir a integridade referencial e a rastreabilidade dos faturamentos e relatórios emitidos.
- **Definição de sem vínculo operacional:** um registro é considerado sem vínculo operacional exclusivamente quando satisfizer todas as seguintes condições:
  1. Nenhum pedido cadastrado (em qualquer status: Aberto, Executado, Faturado ou Pago);
  2. Nenhum ajuste (faturamento complementar) vinculado;
  3. Nenhum faturamento mensal associado.
- Registros que atendam à definição de "sem vínculo operacional" podem ser excluídos definitivamente do banco de dados.
- Ao solicitar a exclusão de um cliente, loja ou produto com vínculo operacional, o sistema realiza a **inativação** (`ativo = 0`). O registro deixa de aparecer em novas seleções de pedidos, mas permanece preservado em históricos, pedidos antigos e relatórios de faturamento.
- **Unicidade de código (Opção A):** o código ou identificador de uma entidade inativa continua protegido pelas restrições de unicidade do banco de dados:
  - Para **Lojas**: a restrição `UNIQUE(cliente_id, codigo_loja)` continua impedindo que outra unidade receba o mesmo código dentro do mesmo cliente, mesmo que a loja original esteja inativa.
  - Para **Produtos**: o nome do produto continua protegido pela restrição `UNIQUE(nome)`.
  - Para **Clientes**: o CNPJ/razão social permanece único.
- **Reativação:** registros inativos podem ser reativados no sistema (`ativo = 1`), mantendo o mesmo identificador/código original e restaurando integralmente o histórico acumulado. A reativação pela interface será definida na fase de cadastros; nesta etapa, o botão não é implementado.

## 4. Produtos e preços

- Cada produto tem um preço padrão, que vem da tabela de produtos.
- Ao lançar um item no pedido, o preço padrão é sugerido, mas pode ser alterado manualmente naquele pedido.
- O preço usado no item é gravado no momento do lançamento. Alterar o preço da tabela depois não muda pedidos já lançados.
- Não existem preços digitados dentro de fórmulas. Todo preço vem da tabela.
- Não podem existir dois produtos com o mesmo nome. Variações de descrição devem ser unificadas ou diferenciadas por código.
- Se um cliente tiver tabela própria, ela substitui o preço padrão para os produtos que ela contém.

## 5. Pedidos

### 5.1 Número
- O número do pedido é digitado pelo usuário, no mesmo formato usado hoje pela empresa (ex.: 20251954).
- O sistema impede que o mesmo número seja usado duas vezes para o mesmo cliente.

### 5.2 Itens
- O pedido tem duas seções: **Serviços** (recargas, testes hidrostáticos, empatação) e **Peças** (manômetro, válvula, mangueira, difusor, trava e similares).
- Cada item tem quantidade, unidade, preço unitário e total (quantidade × preço, com duas casas decimais).
- O total de cada seção e o total geral são calculados automaticamente.
- Itens que não estejam no cadastro podem ser lançados como avulsos, com descrição livre e preço informado. Um item avulso não cria produto no cadastro.

### 5.3 Valor cobrado
- O total do pedido é o valor a ser cobrado. O sistema não aplica nenhum desconto, ajuste ou cobrança adicional além do que foi lançado nos itens.
- Observações registradas no pedido (texto livre) não afetam o cálculo.

### 5.4 Anotações manuais
- Anotações feitas à mão nos pedidos impressos (ex.: itens trocados, condenados, substituições) não são lidas nem calculadas pelo sistema.
- O sistema não tenta interpretar essas anotações. Se o técnico quiser registrar algo que impacte o valor, ele lança como item ou observação.

### 5.5 Duplicação
- A função "duplicar" cria um novo pedido com a mesma loja e cliente, com quantidades e preços zerados. O pedido original não é alterado.

## 6. Status do pedido

- **Aberto**: pedido criado, ainda não executado. Pode ser editado livremente.
- **Executado**: serviço realizado, com data de execução preenchida. Pode ser editado.
- **Faturado**: pedido incluído em um faturamento mensal. Não pode ser editado. Correções são feitas por novo pedido ou ajuste, sem apagar o original.
- **Pago**: opcional, controlado manualmente.
- Faturado pode ser marcado manualmente pelo usuário em qualquer pedido Executado, sem depender do faturamento mensal.

Transições:
- Aberto → Executado: exige data de execução.
- Executado → Faturado: feito pelo faturamento mensal ou manualmente.
- Faturado → Pago: manual.

Não existe campo de número de NF no sistema nesta etapa.

## 7. Faturamento mensal

- Um faturamento reúne os pedidos com status Executado de um cliente, dentro de um período (mês).
- Um pedido só pode estar em um faturamento.
- Ao fechar um faturamento, os pedidos incluídos passam para Faturado.
- Um mesmo mês pode ter mais de um pedido para a mesma loja (ex.: pedido normal e pedido de extras).
- O faturamento tem total por pedido e total geral, e gera PDF.

## 7.1 Faturamento complementar (ajuste de pedido)

Situação: um pedido já faturado pode ter divergência de quantidade quando o prestador de serviço chega à loja (ex.: foram levados mais itens do que o pedido original previa). Nesse caso, o pedido original não é alterado. Um novo faturamento é gerado para registrar a diferença.

### Regras
- Um faturamento complementar (ajuste) sempre pertence a um pedido original já executado.
- O ajuste registra apenas o que foi acrescentado. Itens que não tiveram divergência não entram nele.
- Cada ajuste tem número próprio, vinculado ao pedido original (ex.: 20251954-A1, 20251954-A2). A forma de numeração ainda precisa ser confirmada.
- Um pedido pode ter vários ajustes, mas cada ajuste só pode ser faturado uma vez.
- Itens do ajuste usam as mesmas regras de preço da seção 4: preço padrão da tabela, editável no ajuste, gravado no item.
- O ajuste entra no faturamento mensal da mesma forma que um pedido executado, sem alterar o status do pedido original.

### Formas de geração (o usuário escolhe no momento de gerar)
1. **Somente a diferença**: o PDF lista apenas os itens acrescentados, com quantidade, preço unitário e total. O valor a cobrar é a soma desses itens.
2. **Valores incrementados**: o PDF mostra o pedido completo atualizado. Para cada item, aparecem a quantidade original, a quantidade acrescentada, a quantidade final e o total final. O valor a cobrar é o total final menos o que já foi faturado no pedido original.

### Totais do pedido
- O sistema mantém o histórico: valor original faturado, cada ajuste e valor total acumulado do pedido.
- A tela do pedido mostra os ajustes vinculados e o total acumulado.

## 8. Condições comerciais

- Cada cliente tem condições padrão: prazo de pagamento (ex.: 30 dias), forma de pagamento (ex.: depósito ou transferência) e prazo de entrega/produção (ex.: 7 dias úteis).
- Essas condições aparecem no pedido e podem ser alteradas naquele pedido.
- A observação "impostos inclusos" é texto configurável no cliente ou no pedido. O sistema não calcula impostos.

## 9. Conteúdo do PDF

PDF do pedido:
- Cabeçalho do emitente: nome, endereço, telefone, CNPJ e Inscrição Estadual.
- Dados do cliente: razão social, nome fantasia, CNPJ, IE, endereço, loja/código, cidade, UF, CEP, telefone e contato.
- Número do pedido, data de emissão e data de execução.
- Tabela de serviços e tabela de peças, cada uma com item, código, descrição, quantidade, unidade, preço unitário e total.
- Subtotais por seção e total geral.
- Condições de pagamento, forma de pagamento, prazo de entrega e observações.
- Campos de "aceite do cliente" e "autorizado por" para assinatura manual.

PDF do faturamento mensal:
- Cabeçalho, dados do cliente e período.
- Lista de pedidos incluídos, com número, data, loja e total.
- Total geral do período.

## 10. Vencimento dos extintores

- O status de cada loja (VENCIDO ou NA VALIDADE) é calculado comparando a data de vencimento com a data atual.
- VENCIDO só depois que o mês de vencimento terminou. No próprio mês de vencimento a loja continua NA VALIDADE (exemplo: vencimento 10/2026 → NA VALIDADE até 31/10/2026, VENCIDO a partir de 01/11/2026).
- Vencidos são destacados na tela. Nenhum registro é apagado automaticamente.
- Regra da coluna PESAGEM (vencimento menos 180 dias): pendente de definição.

## 10.1 Visualização em formato de planilha

- Cada cadastro e cada listagem (lojas, produtos, pedidos, itens, faturamentos, histórico) pode ser exibido em grade, no formato de planilha.
- Na grade, o usuário pode ordenar por coluna, filtrar por qualquer coluna (inclusive status, cliente, bandeira e UF), buscar texto e escolher quais colunas exibir.
- Exportar para Excel (.xlsx) respeita os filtros e a ordenação atuais. O que está na tela é o que sai no arquivo.
- Exportar também está disponível para CSV.
- Importação: o sistema lê as planilhas atuais (manutenções mensais e controle de produtos e entregas) para carregar o histórico, com validação e relatório de linhas ignoradas ou com erro.

## 11. Pendências em aberto

6. Significado de "NOTIFICADA" na observação: quem notifica, o que a notificação exige e se afeta o faturamento.
7. Significado de "ENCAIXE DE ROTEIRO" e de "CT" e "CASA" nos nomes dos sites.
8. Critério do período de faturamento: a aba do mês ou a data de atendimento. Hoje as duas podem divergir.
9. Status de faturamento do histórico: como identificar quais atendimentos já foram faturados, já que a coluna só está marcada em 5 linhas.

1. Regra exata da PESAGEM (alerta de antecedência ou outro cálculo).
   - Pendente. A coluna da planilha de manutenções não traz esse dado com clareza.
   - NOTIFICADA: ainda não se sabe se bloqueia o faturamento ou é só informativa. Fica como chave de alerta marcável pelo usuário até definição.
   - Status FINALIZADA/FECHADO/4° REMESSA do histórico: não se sabe o significado. Essas marcações ficam para o usuário decidir, sem conversão automática para Faturado.
2. Se o PDF do faturamento precisa de totais por produto, além dos totais por pedido.
3. Numeração dos ajustes: sufixo sobre o número do pedido (20251954-A1) ou outro formato?
4. Divergência para menos (o prestador levou menos itens do que o previsto): também deve ser possível gerar um ajuste com valor negativo, ou só acréscimos?
5. Na opção "valores incrementados", confirmar se o valor a cobrar é a diferença entre o total final e o já faturado, como descrito na seção 7.1.
