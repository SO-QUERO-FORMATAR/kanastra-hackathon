# Planejamento sequencial do backend Antecipe

Base: `Antecipe_Documentacao_do_Sistema.pdf`, versão 2.1 de 24/10/2026.

Planejamento de 24/10/2026, atualizado durante a implementação. T00 mantém o contrato original; os marcadores abaixo registram implementação e verificação das tarefas. Evidências e pendências de aceitação estão no [checklist de execução](execucao/checklist.md). A aceitação oficial de T16 e a conclusão integral de T18 continuam dependentes das inconsistências dos insumos; implementação não equivale a aprovação do gabarito.

## Pacote obrigatório para backend e frontend

- [Contrato de fluxos e decisões](contrato-api.md).
- [OpenAPI com todos os requests/responses](contratos/openapi.json), [catálogo campo a campo](contratos/dtos.md), [tipos TypeScript](contratos/api-types.ts) e [exemplos JSON](contratos/exemplos.json).
- [Prompt autocontido para o outro contexto do frontend](handoff-frontend.md): inclui integralmente os schemas JSON, exemplos de todas as DTOs e operações, sem depender de acesso ao repositório.
- [Auditoria dos insumos](auditoria-insumos.md) e [evidências estruturadas/hashes](auditoria-insumos.json).

O contrato v1.0.0 é a fonte de integração. As escolhas técnicas e os DTOs nele definidos prevalecem sobre propostas abertas da primeira versão deste plano. Alterações incompatíveis devem ser coordenadas entre frontend e backend antes da implementação.

## Diretrizes e escopo

- Python 3.11+, FastAPI, SQLAlchemy 2.0 e PostgreSQL 16+, conforme a especificação.
- Monólito modular com arquitetura hexagonal: domínio independente de HTTP, banco e arquivos; aplicação coordenando portas; adaptadores concretos nas bordas.
- Moeda, taxas, PL e exposição em `Decimal`, sem conversão intermediária para `float`.
- CSV e XLSX, armazenamento local persistente, worker fora do processo/event loop da API, processamento em duas passagens e paginação por cursor.
- Todos os arquivos válidos do manifesto compõem o contexto do lote; preservar a ordem do manifesto e das linhas, independentemente da ordem de chegada dos uploads.
- Unicidade operacional pela combinação dos documentos normalizados de cedente e sacado com `NU_DOCUMENTO` textual. `NOTA_DUPLICADA` permanece obrigatório e separado dos nove validadores configuráveis.
- Apenas aprovações registram a chave operacional e incrementam as duas exposições. Barramentos têm desconto e valor líquido iguais a `0.00`.
- A versão das regras é fixada por lote na primeira transição para ANALISANDO, após resolver todos os fundos pendentes. A carga cadastral utilizada também deve permanecer estável durante processamento e recuperação.
- Cada fundo exige configuração própria, conforme decisão do usuário. Os 17 fundos sem regras geram bloqueios visíveis na API, sem replicação automática das regras do ANTECIPE.
- O frontend não faz parte deste plano; os contratos necessários à sua integração fazem.

Ferramentas propostas para execução: `pytest`, `pytest-cov`, testes HTTP com `httpx`, migrações com Alembic e CI no GitHub Actions. São escolhas de implementação, além da stack definida pelo PDF.

## Regra obrigatória para avançar

Em **toda tarefa**, seguir este ciclo:

1. Escrever os testes de aceitação da tarefa, com entradas e saídas explícitas, e comprovar que falham pelo comportamento ainda ausente.
2. Implementar o comportamento mínimo necessário.
3. Executar os testes novos e a suíte de regressão acumulada das tarefas anteriores.
4. Refatorar mantendo a suíte verde e atualizar contratos/documentação afetados.
5. Registrar os comandos executados, resultado, limitações e evidências antes de marcar a tarefa como concluída.

Não avançar com falhas, testes críticos ignorados ou regressões sem resolução. Correções de defeitos devem incluir um teste que reproduza o defeito antes da correção. Testes de concorrência e transação devem usar PostgreSQL real, não SQLite nem mocks do banco.

## Sequência de tarefas

### [x] T00 — Fechar e validar o contrato de integração

**Entrega:** 17 operações HTTP, schemas tipados de request/response, DTOs de query, envelope de erro, unions dos nove validadores, estados e transições, manifesto e multipart, idempotência, versão de regras, recuperação, paginação e fixtures. Tipos TypeScript e catálogo gerados da mesma definição OpenAPI. A auditoria integral substitui a hipótese de que os arquivos ainda estavam ausentes.

**Verificações:** integridade estrutural do OpenAPI, resolução dos schemas, validação dos exemplos e compilação dos tipos TypeScript. Essas verificações conferem o contrato; não substituem os testes de implementação previstos nas tarefas seguintes.

**Conclusão:** frontend e backend podem ser planejados com os mesmos DTOs. A inconsistência da referência é uma pendência explícita de aceitação de negócio, não uma lacuna de transporte HTTP.

### [x] T01 — Preparar estrutura, ambiente e execução dos testes

**Dependência:** T00.

**Implementação:** criar `backend/`, configuração de dependências reproduzível, diretórios `domain/`, `application/`, `ports/` e `adapters/`; configurar pytest, lint, tipagem e CI inicial. Disponibilizar PostgreSQL de teste isolado e documentação dos comandos locais. A esteira deve falhar se a suíte esperada não for coletada. Incorporar validação/regeneração do contrato e manter fixtures compartilhadas com frontend.

**Testes:** verificar carregamento da aplicação mínima e configuração; um teste de arquitetura deve impedir dependências de FastAPI/SQLAlchemy no domínio. Validar conexão com o banco de teste sem acessar bases de uso normal.

**Conclusão:** instalação e execução reproduzíveis em ambiente limpo, com CI executando testes reais. Nenhum teste vazio ou que apenas use `assert True`.

### [x] T02 — Definir entidades, documentos e identidade dos títulos

**Dependência:** T01.

**Implementação:** entidades de fundo, título, origem e resultado; documentos normalizados como texto; raiz de oito dígitos; chave operacional; prazo em dias corridos a partir das datas da nota. Preservar dados originais para rastreabilidade.

**Testes:** CNPJ mascarado e sem máscara, zeros iniciais, 14 dígitos, DVs inválidos, letras e sequências inválidas; matriz/filial com mesma raiz; `000351153` e `1-759172` preservados; mesmo número com cedente/sacado diferente produz chave distinta; prazo zero, negativo e ano bissexto. Cobrir VAL01 e DUP02.

**Conclusão:** domínio sem dependências externas e normalização sem corrigir silenciosamente documentos inválidos.

### [x] T03 — Definir contrato e validação da configuração dos fundos

**Dependência:** T02.

**Implementação:** carregar `fundo`, `validadores` e `precificacao`; validar códigos, flags booleanas e parâmetros; mapear `parametros.percentual_maximo`; representar versão imutável da configuração e associação pelo CNPJ do fundo. Validar combinações incoerentes, como prazo mínimo maior que máximo, base de dias não positiva e códigos repetidos.

**Testes:** configuração fornecida com sete regras ativas e duas inativas; preservação dos parâmetros inativos; código desconhecido, parâmetro ausente e tipo inválido; taxa decimal sem perda; método de precificação inválido; fundo sem configuração gera pendência; `NOTA_DUPLICADA` continua obrigatório mesmo ausente do JSON. Cobrir CFG01, CFG03 e CFG04 com fixture sintética e com `files/validadores_antecipe.json`. Validar nove códigos únicos, transformação de números do arquivo para strings HTTP e agrupamento RAIZ_CNPJ do cedente.

**Conclusão:** configuração inválida não pode ser ativada, e valores do exemplo não estão fixados no motor.

### [x] T04 — Implementar os validadores individuais

**Dependência:** T03.

**Implementação:** CNPJ, situação cadastral, tipo de recebível, valor mínimo, não vencida, prazo mínimo e máximo; cada regra retorna código e dados para explicação parametrizada. Receber situação cadastral por uma porta, sem consultar o banco dentro do domínio.

**Testes:** sucesso e falha para cada regra, incluindo limites exatos; valor mínimo menos um centavo; prazo mínimo/máximo menos um, igual e mais um dia; prazo zero ou negativo reprovado por `NAO_VENCIDA`; prazo positivo sujeito a `PRAZO_MINIMO`; cadastro ausente, aceito e não aceito; desativação de cada regra impede seu barramento. Cobrir VAL01–VAL07 e CFG01.

**Conclusão:** todos os códigos são os oficiais e mensagens refletem os parâmetros efetivamente aplicados.

### [x] T05 — Implementar PL e concentração por fundo e raiz

**Dependência:** T04.

**Implementação:** apurar PL pela soma nominal de todas as notas do fundo no contexto, inclusive notas que depois sejam barradas; calcular tetos; avaliar exposição anterior mais novo nominal para sacado e cedente, sem mutação antecipada dos saldos.

**Testes:** múltiplos fundos e arquivos; raízes iguais em fundos diferentes; matriz/filiais compartilhando exposição; saldo anterior; igualdade ao limite aprova e excesso de um centavo barra; nota barrada não altera PL já apurado nem consome exposição. Cobrir CON01–CON03.

**Conclusão:** nenhuma decisão de concentração ocorre antes do PL completo e não há soma em ponto flutuante.

### [x] T06 — Implementar precificação com precisão decimal

**Dependência:** T05.

**Implementação:** aplicar desconto simples com precisão Decimal de 38 dígitos; calcular desconto como `(nominal * taxa_mensal_percentual * prazo) / (100 * base_dias)` sem quantização intermediária de taxa. Quantizar desconto no fechamento do título em centavos com `ROUND_HALF_UP`; líquido por diferença. Somar valores fechados nos resumos. Conforme contrato final, aplicar fórmula literalmente quando regras forem desativadas, preservando eventual valor negativo sem clamp ou nova recusa implícita.

**Testes:** nominal `10000.00`, prazo 30, taxa mensal 2 e base 30 resultam em desconto `200.00` e líquido `9800.00`; taxa zero; prazo zero; frações de centavo; valores grandes; prazo negativo com regras de prazo desativadas; desconto superior ao nominal; barrado com desconto e líquido `0.00`. Verificar `nominal = desconto + líquido` para aprovados e round-trip HTTP com strings. Cobrir FIN01, FIN02 e REF03.

**Conclusão:** política monetária registrada e valores esperados calculados independentemente da implementação.

### [x] T07 — Integrar o motor determinístico em memória

**Dependência:** T06.

**Implementação:** compor unicidade, regras ativas, concentração e precificação. Duplicidade já conhecida encerra a avaliação com `NOTA_DUPLICADA`; nos demais casos, acumular motivos das regras aplicáveis. Atualizar chave e ambos os saldos somente depois da aprovação completa, inclusive o saldo associado a uma regra de concentração desativada.

**Testes:** fluxo aprovado; múltiplos motivos; duplicidade no próprio lote e no histórico; tentativa inicialmente barrada não reserva chave; sacado passa e cedente falha sem atualização parcial; desativar uma regra não desativa as demais; repetir com mesmo contexto inicial e ordem produz o mesmo resultado. Cobrir DUP01 e consolidar regressão de VAL, CON, CFG e FIN.

**Conclusão:** motor completo validado sem banco, arquivos ou HTTP.

### [x] T08 — Criar esquema relacional, migrações e repositórios

**Dependência:** T07.

**Implementação:** tabelas de fundos, versões de regras, carga cadastral, lotes, manifesto/arquivos, resultados/motivos, títulos aprovados, exposições e controle de execução/checkpoints. Criar constraints, índices de consulta e unicidade global da chave operacional entre aprovações. Resultados barrados podem repetir essa chave; identidade de processamento usa lote/arquivo/linha. Usar tipos numéricos exatos com precisão compatível com os limites documentados.

**Testes:** migrações em banco vazio; persistência e leitura sem perda decimal; integridade referencial; aprovação duplicada rejeitada pelo banco, inclusive entre fundos; barramentos repetidos permitidos; resultado de mesma origem não duplicado; rollback sem dados parciais.

**Conclusão:** invariantes essenciais protegidas também por PostgreSQL, com testes de integração isolados.

### [x] T09 — Implementar carga cadastral e publicação das regras

**Dependência:** T08.

**Implementação:** importação administrativa separada do upload de notas, via caso de uso/CLI; CSV cadastral `DOC;SITUACAO_CADASTRAL`, normalização, carga em lote e publicação transacional. Importar o cadastro fornecido para tabela PostgreSQL indexada e regras somente para o fundo identificado no JSON. Descobrir/cadastrar os outros fundos durante indexação, sem configuração automática. Fixar versões antes da primeira análise. Impedir substituição cadastral enquanto houver job ativo ou recuperável vinculado à base, incluindo a corrida entre worker e importação. Consultar documentos distintos por batch e reutilizar respostas.

**Testes:** reimportação idêntica sem duplicação; CNPJs com situações conflitantes geram erro explícito; falha de carga preserva versão anterior; base ausente impede preparação, enquanto CNPJ ausente em base disponível barra a nota; consulta agrupada, sem uma consulta por linha; regras novas só afetam lotes novos; carga cadastral concorrente não altera lote em execução. Cobrir CAD01–CAD03 e CFG02–CFG04.

**Conclusão:** processamento pode obter contexto válido, estável e auditável antes de ler o estoque.

### [x] T10 — Garantir aprovação transacional e concorrência

**Dependência:** T09.

**Implementação:** coordenar leitura atualizada de exposição, verificação de unicidade, aprovação, ambos os saldos, resultado e checkpoint em transação. Definir locks por fundo/raízes e ordem fixa de aquisição; usar a constraint global para disputas de chave entre fundos. O snapshot inicial não substitui a releitura protegida dos saldos antes do commit. Em conflito, desfazer e reavaliar a unidade afetada sem reaproveitar saldo obsoleto.

**Testes:** duas conexões sincronizadas disputando a mesma nota resultam em uma aprovação; notas distintas disputando o mesmo limite não excedem o teto; conflitos entre fundos; falha entre registro da chave e atualização dos saldos desfaz tudo; retries não duplicam efeitos; resultados barrados continuam persistidos. Usar barreiras de sincronização em vez de depender de sleeps. Cobrir CONC01 e DUP01.

**Conclusão:** banco garante unicidade e concentração sob disputa real; a ordem dentro de cada lote continua determinística. A ordem entre lotes concorrentes deve ser documentada, sem prometer o mesmo vencedor em execuções diferentes.

### [x] T11 — Implementar leitores CSV e XLSX

**Dependência:** T10.

**Implementação:** leitores por chunks preservando arquivo e linha; CSV UTF-8 com/sem BOM, `;`, vírgula decimal e datas `dd/mm/aaaa`; XLSX via calamine com fallback openpyxl read-only, conforme o PDF. Validar as 11 colunas obrigatórias. Não executar macros ou fórmulas; definir tratamento de células com fórmula sem valor disponível. Documentar tratamento de células numéricas de Excel para evitar perda adicional de precisão e de zeros dos identificadores.

**Testes:** arquivos mínimos CSV/XLSX equivalentes; acentos, BOM, máscaras, zeros e hífens; linhas vazias; datas/valores inválidos; cabeçalho ausente; arquivo corrompido; comportamento de abas e fórmulas. Erro estrutural marca arquivo `FALHOU`; erro de dados preserva origem e permite continuar as outras linhas. Cobrir ARQ01.

**Conclusão:** leitores distinguem falha de arquivo, diagnóstico ERRO_DADOS e recusa financeira. Aplicar contrato final: erro de data preserva nominal/fundo no PL e não para outras notas; nominal/fundo ilegível bloqueia o lote antes da análise com DADOS_IMPEDEM_PL, exigindo correção em novo lote. Arquivo estruturalmente inválido não contribui para PL e pode resultar em conclusão parcial dos demais. Não criar novo código FIDC para parsing.

### [x] T12 — Implementar manifesto, armazenamento e uploads idempotentes

**Dependência:** T11.

**Implementação:** criar lote com IDs e ordem estáveis; salvar arquivos em diretório persistente usando IDs internos; conferir SHA-256, tamanho, identidade e conclusão do manifesto. Implementar CriarLoteRequest/Response, BatchMetadadosDTO e confirmação atômica do batch. Mesma chave com conteúdo diferente retorna 409; mesmo conteúdo retorna resposta persistida. Permitir retry do batch; nenhum upload inicia o motor automaticamente. POST processamento sela o manifesto.

**Testes:** upload de 1 e 3 arquivos, rejeição de 4; limite de 64 MiB e excesso; tipo não suportado; arquivo fora do manifesto; upload incompleto/corrompido; ordem de chegada diferente da seleção; chave repetida com conteúdo igual/diferente; reenvios simultâneos; nomes com tentativa de sair do diretório; falha ao gravar disco sem registro de sucesso indevido.

**Conclusão:** upload repetido não cria operações e o início exige todos os itens recebidos; limites e multipart obedecem ao contrato. Falha estrutural descoberta na indexação marca o arquivo FALHOU e remove sua contribuição parcial de PL, sem alterar bytes do manifesto.

### [x] T13 — Implementar worker em duas passagens e recuperação

**Dependência:** T12.

**Implementação:** worker dedicado com reivindicação persistida de trabalho, recuperação após falha e execução fora da API. Primeira passagem valida/normaliza, descobre fundos, consolida PL e publica pendências; sem regras por fundo/base disponível, transiciona para BLOQUEADO antes de qualquer aprovação. Após resolução, congela contexto e segunda passagem aplica motor em ordem estável. Persistir batches de 1.000 a 5.000 resultados, progresso e checkpoint com o commit; usar staging limitado para não manter 500 mil objetos em memória. Retomada segue AcoesLoteDTO e contexto original quando análise já começou.

**Testes:** PL completo antes da primeira decisão; múltiplos arquivos/fundos; arquivo falhando sem contaminar PL com soma parcial; mesmo resultado com diferentes tamanhos de batch; dois workers não executam o mesmo trecho; interrupção antes/depois do commit e retomada sem perda ou duplicação. Uma aprovação já persistida pelo próprio job deve ser recuperada como resultado existente, sem virar um novo barramento por duplicidade. Nova operação com a mesma nota continua sendo `NOTA_DUPLICADA`.

**Conclusão:** reexecução mantém resultados, chaves, exposições e totais equivalentes a uma execução sem interrupção.

### [x] T14 — Expor API de lotes, progresso e regras

**Dependência:** T13.

**Implementação:** implementar as 16 operações de infraestrutura/capacidades/cadastro/fundos/regras/lotes/arquivos/resumos/pendências do OpenAPI, deixando somente listarResultados para T15. Isso inclui histórico, GET de regras atuais/históricas e POST explícito de início/retomada. Reproduzir DTOs, envelopes de erro, ações disponíveis e estados; prefixo `/api/v1`, CORS e correlação. Edição de regras usa versao_base e chave idempotente. Listagens auxiliares usam cursor. Bytes de transferência são acompanhados no cliente; backend informa recebimento persistido.

**Testes:** cobrir cada operationId e seus DTOs de sucesso/erro, IDs inexistentes, payload inválido, nulos, campos extras, conflito idempotente e edição concorrente. Testar bloqueio por 17 fundos sem regras, configuração individual e retomada; falha parcial; versões congeladas; progresso/checkpoint e resumo reconciliado. Upload/início não aguardam análise. Validar respostas reais contra OpenAPI compartilhado e exemplos contra os mesmos schemas.

**Conclusão:** frontend consegue criar, enviar e acompanhar um lote somente pelos contratos publicados.

### [x] T15 — Implementar consulta por cursor e filtros

**Dependência:** T14.

**Implementação:** operationId listarResultados, com limit/cursor/status/motivo/tipo e union ResultadoDTO. Cursor opaco autenticado fixa arquivo, filtros, limit e teto do snapshot. Retornar ResultadosPageResponse; valores decimais em strings, estados ERRO_DADOS separados de decisões APROVADO/BARRADO. Não expor offset ou total de páginas arbitrário. Atualização da primeira página cria snapshot novo.

**Testes:** primeira/última página e arquivo vazio; cursor inválido ou de outro arquivo/filtro; ausência de repetições/lacunas em conjunto concluído; filtro por cada motivo e status; resultado com múltiplos motivos aparece uma única vez; limite inválido; novos resultados durante processamento respeitam a semântica documentada. Cobrir PAG01 funcionalmente; latência será medida em T17.

**Conclusão:** API consulta somente a página solicitada e usa índices compatíveis com ordenação e filtros.

### [ ] T16 — Validar fluxo completo e comparar arquivos de referência

**Dependência:** T15; os quatro arquivos oficiais já estão em `files/`. Aceitação sem divergências depende de resolução das inconsistências documentadas na auditoria.

**Implementação:** cenário ponta a ponta com PostgreSQL, storage, API e worker reais; comparador separado do motor. Preparar cadastro, regras, estado inicial de aprovados/exposições, manifesto e upload; comparar por arquivo, linha e `NU_DOCUMENTO` textual. O JSON esperado nunca participa da decisão do motor.

**Testes:** primeiro executar fixture sintética pequena cobrindo aprovações, todas as recusas, reenvio e retomada. Depois processar o CSV oficial completo e comparar identificação, status e conjunto de motivos; ausência de motivos em aprovado equivale a lista vazia. Detectar faltantes, extras, IDs divergentes e duplicados no próprio gabarito. Cobrir REF01–REF03.

**Conclusão:** fluxo sintético integral verde e comparador reproduzível, com relatório das divergências oficiais por linha, regra, versão e contexto. O gabarito atual aprova chaves duplicadas e sacados ausentes: zero divergências não é um critério alcançável mantendo esses dados e as regras. A aceitação oficial só encerra após corrigir/explicar insumos e fornecer configurações/estado inicial, ou revisar expressamente o requisito. Não ajustar resultados manualmente nem enfraquecer testes para satisfazer o gabarito.

### [x] T17 — Validar volume, latência e estabilidade

**Dependência:** T16, ao menos seu cenário sintético integral.

**Implementação:** gerador determinístico de 100 mil e 500 mil notas e rotina de benchmark reproduzível. Medir tempo total, consumo máximo de memória, consultas cadastrais, escrita em lote e latência da API durante o processamento; otimizar a partir dos resultados.

**Testes:** processamento completo dos dois volumes, incluindo exercício de CSV/XLSX; contagem e somas sem perdas; consultas por documentos distintos; memória limitada pela estratégia de chunks; ausência de timeout HTTP; p95 de consulta ≤ 300 ms para páginas de até 100 registros com filtros representativos. Registrar hardware, índices, concorrência, aquecimento e amostragem. Se houver otimização, repetir os testes funcionais afetados.

**Conclusão:** evidências de desempenho reproduzíveis e meta de consulta atendida. O PDF não fixa prazo total de processamento nem teto de RAM: estabelecer orçamento medido no ambiente alvo, sem inventar SLA.

### [ ] T18 — Fechar operação, documentação e regressão de entrega

**Dependência:** T17 e resolução das pendências de aceitação de T16 para declarar conclusão integral.

**Implementação:** documentar setup, migrações, cargas, execução da API/worker, recuperação, contratos e limitações. Logs com lote/arquivo/fase/linha e versão, sem despejar conteúdo completo das notas. Disponibilizar verificações de saúde/prontidão e comandos de teste. Consolidar CI com testes unitários, integração e contratos a cada mudança; volume completo em rotina manual de entrega ou agendada.

**Testes:** inicialização em ambiente limpo; banco indisponível; configuração/base ausente; reinício de worker com job pendente; migração seguida de fluxo completo. Executar a suíte acumulada e a aceitação oficial antes da entrega; guardar relatórios de volume.

**Conclusão:** outra pessoa consegue instalar, testar e operar o backend seguindo a documentação, com todas as evidências de validação disponíveis.

## Organização prevista dos testes

```text
backend/tests/
  unit/          # documentos, regras, PL, concentração, precificação e motor
  application/   # casos de uso com portas controladas
  integration/   # PostgreSQL, migrações, locks, storage e leitores reais
  api/           # contratos HTTP, idempotência, filtros e cursores
  e2e/           # API + worker + banco + arquivos
  acceptance/    # comparação com referência oficial
  performance/   # 100k/500k, memória e p95
  fixtures/      # dados sintéticos pequenos e versões conhecidas
```

Mocks são apropriados para isolar portas nos testes de domínio/aplicação. Não substituem a validação real dos adaptadores, transações, recuperação ou fluxo completo. Relatórios de cobertura ajudam a identificar lacunas; cobertura percentual não substitui os cenários de integridade.

## Decisões fechadas e pendências de aceitação

O contrato fecha arredondamento, serialização decimal, estado ERRO_DADOS, bloqueio quando não há PL confiável, conclusão parcial, início explícito, congelamento na primeira análise, edição otimista, multipart, cursor e ambiente de demonstração sem autenticação. Esses pontos não ficam a critério independente do frontend e do backend.

Continuam pendentes **dados de negócio**, não DTOs:

1. Configurações específicas dos outros 17 fundos; a API fornece o fluxo para cadastrá-las.
2. Cadastro/gabarito compatíveis: 1.406 sacados distintos ausentes, incluindo 712 aprovações do ANTECIPE sem cadastro.
3. Correção/explicação de 4.941 aprovações repetidas da mesma chave no gabarito.
4. Estado inicial de exposições/aprovações usado para gerar a referência.

Essas pendências não impedem T01–T15, testes sintéticos nem planejamento do frontend. Impedem certificar concordância integral com o gabarito atual. Preservar os arquivos e hashes originais; qualquer revisão terá sua própria auditoria.

## Mapeamento de tarefas aos contratos

| Tarefa | DTOs/contratos centrais |
|---|---|
| T02–T07 | TituloNormalizadoDTO, CodigoRecusa, MotivoDTO, ResultadoDTO; regras puras |
| T03/T09 | ConfiguracaoRegrasDTO, ValidadorDTO, PrecificacaoDTO, BaseCadastralStatusResponse |
| T08/T10 | Persistência das identidades, snapshots, idempotência, estados e atomicidade que sustentam os DTOs |
| T11 | DadosOriginaisTituloDTO, ErroDadoDTO, ResultadoErroDadosDTO, PendenciaDTO |
| T12 | CriarLoteRequest/Response, ArquivoManifestoRequest, BatchMetadadosDTO, EnviarBatchRequest/Response |
| T13 | ProcessarLoteResponse, StatusLote, StatusArquivo, ProgressoDTO, AcoesLoteDTO |
| T14 | Todos os DTOs de listagem/estado/regras/saúde/capacidades, ErroResponse e DTOs de query correspondentes |
| T15 | ListarResultadosQuery, ResultadosPageResponse e variantes ResultadoAprovado/Barrado/ErroDadosDTO |
| T16–T18 | Contrato completo, testes reais de consumidor/provedor e evidências de aceitação/desempenho |

## Critério final de integridade

O backend só estará integralmente validado quando todas as tarefas/dependências estiverem verificadas: nenhuma venda duplicada sob concorrência; nenhuma exposição alterada por título barrado; nenhum efeito duplicado após retry; precisão decimal preservada; contexto estável; resultados rastreáveis; conformidade com os DTOs compartilhados; pendências de referência resolvidas com comparação reproduzível; e processamento de 100 mil a 500 mil linhas com a meta de paginação comprovada.









