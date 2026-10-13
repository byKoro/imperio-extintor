# Regras de Inativação e Reativação de Cadastros

## 2.1 Inativação e reativação de cadastros (Clientes, Lojas e Produtos)

### Regra Geral
- Entidades cadastradas no sistema (**clientes**, **lojas** e **produtos**) que possuam qualquer vínculo com o histórico operacional ou financeiro não podem ser excluídas fisicamente do banco de dados, para garantir a integridade referencial e a rastreabilidade dos faturamentos e relatórios emitidos.

### Definição de "Sem Vínculo Operacional"
- Um registro é considerado **sem vínculo operacional** exclusivamente quando satisfizer todas as seguintes condições:
  1. **Nenhum pedido** cadastrado (em qualquer status: Aberto, Executado, Faturado ou Pago);
  2. **Nenhum ajuste** (faturamento complementar) vinculado;
  3. **Nenhum faturamento mensal** associado.

### Comportamento da Exclusão e Inativação
1. **Com vínculo operacional:**
   - Ao solicitar a exclusão de um cliente, de uma loja ou de um produto que possua vínculo com pedidos, ajustes ou faturamentos, o sistema não apaga o registro, mas realiza a sua **inativação** (`ativo = 0`).
   - Registros inativados deixam de ser exibidos nas listagens e caixas de seleção padrão para novos lançamentos de pedidos.
   - Registros inativados permanecem preservados em consultas históricas, pedidos já emitidos e relatórios de fechamento mensal.
2. **Sem vínculo operacional:**
   - Registros recém-criados ou criados por engano que atendam estritamente à definição de "sem vínculo operacional" podem ser excluídos definitivamente do banco de dados.

### Tratamento de Unicidade de Código (Opção A)
- O código/identificador de uma entidade inativada continua bloqueado pelas restrições de unicidade do banco de dados:
  - Para **Lojas**: a restrição `UNIQUE(cliente_id, codigo_loja)` continua impedindo que outra unidade receba o mesmo código dentro do mesmo cliente, mesmo que a loja original esteja inativa.
  - Para **Produtos**: o nome do produto continua protegido pela restrição `UNIQUE(nome)`.
  - Para **Clientes**: o CNPJ/razão social permanece único.

### Reativação de Cadastros
- Registros inativos podem ser reativados no sistema (retornando a `ativo = 1`).
- A reativação mantém o mesmo identificador/código original e restaura todo o histórico de atendimentos, pedidos e configurações comerciais acumulados, tornando a entidade novamente disponível para novos atendimentos.
