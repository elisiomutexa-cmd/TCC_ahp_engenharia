# SAD AHP Engenharia

Aplicação Django de apoio à decisão para seleção de fornecedores de serviços de engenharia. Implementa o **Analytic Hierarchy Process (AHP)**, comparações pareadas pela escala de Saaty, verificação de consistência e relatório auditável da decisão.

## Capacidades

- autenticação com perfis Administrador e Gestor/Avaliador;
- CRUD de fornecedores, serviços, critérios e subcritérios dinâmicos;
- assistente de avaliação: serviço → fornecedores → critérios → comparações → consistência → ranking;
- pesos por normalização da matriz e média das linhas;
- λmax, CI, RI e **CR = CI / RI**; CR inferior a 0,10 é considerado aceitável;
- prioridades locais, globais, fornecedor recomendado, histórico e auditoria;
- dashboard Chart.js, PDF, CSV, Excel e impressão;
- anexos de propostas por fornecedor (PDF, Word, Excel e imagens);
- gráfico vetorial de pesos e gráfico de ranking incorporados no PDF;
- tabela RI editável no Django Admin, aplicada automaticamente ao motor AHP;
- dados fictícios de demonstração e testes automatizados do motor AHP.

## Arquitetura

`templates → views → EvaluationAHPService → AHPDecisionEngine → Django ORM → MySQL`

Os módulos ficam em `apps/accounts`, `suppliers`, `services`, `criteria`, `evaluations`, `ahp`, `reports`, `dashboard` e `audit`. O cálculo está isolado em `apps/ahp/engine.py`; as views não contêm a matemática AHP.

## Instalação e MySQL

1. Crie uma base MySQL UTF-8: `CREATE DATABASE ahp_engenharia CHARACTER SET utf8mb4;`.
2. Crie o ambiente virtual e instale as dependências: `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e preencha `SECRET_KEY`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`. Nunca versione o `.env`.
4. Execute `python manage.py migrate`.
5. Opcionalmente crie um administrador: `python manage.py createsuperuser`.
6. Crie a demonstração: `python manage.py seed_data`.
7. Inicie: `python manage.py runserver`.

O MySQL é o padrão para a aplicação. `python manage.py test` usa automaticamente uma base SQLite isolada, portanto não requer MySQL em execução. Para desenvolver localmente sem MySQL, defina `USE_SQLITE=True`; isto não é indicado para produção.

## Demonstração

`python manage.py seed_data` cria informação explicitamente fictícia, incluindo quatro fornecedores, o serviço HVAC e o catálogo de critérios/subcritérios. Também cria uma decisão calculada. Credenciais iniciais: `admin` / `Admin@12345` (altere a palavra-passe imediatamente em qualquer ambiente não descartável).

## Testes

Execute `python manage.py test`. O caso conhecido em `apps/ahp/tests.py` valida pesos 0,6000 / 0,3000 / 0,1000, λmax = 3, CI = 0 e CR = 0. Os testes cobrem reciprocidade e ranking normalizado.

## Administração da tabela RI

Após executar as migrations, abra `/admin/` e aceda a **Tabela de índices aleatórios (RI)**. Os valores padrão de Saaty para n=1 a n=15 são carregados automaticamente. É possível corrigir um RI, desativar uma linha ou acrescentar ordens superiores; a alteração é usada no próximo cálculo de uma avaliação.

## Algoritmo

A matriz respeita `aij = 1/aji` e `aii = 1`. Cada coluna é normalizada e o peso é a média da respetiva linha. Para cada matriz, `CI = (λmax - n)/(n - 1)` e `CR = CI/RI`. Para n ≤ 2, a matriz é tratada como trivialmente consistente. Em hierarquias com subcritérios, o peso global da folha é `peso(pai) × peso(subcritério)`. A prioridade global de cada fornecedor é a soma ponderada das prioridades locais.

## Segurança e rastreabilidade

O sistema usa autenticação Django, CSRF, hash de palavras-passe, ORM, validação por formulários, permissões por papel, snapshots de fornecedores/critérios dentro das avaliações concluídas e `AuditLog` para ações relevantes.

## Melhorias futuras

Docker Compose, anexos de propostas, relatórios com gráfico incorporado e uma tabela RI parametrizável na interface administrativa.
