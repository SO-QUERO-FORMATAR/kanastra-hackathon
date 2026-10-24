# Decisões de implementação

O domínio (`antecipe/domain`) usa somente biblioteca padrão: entidades, documentos,
configuração imutável, regras, PL/concentração, preço e avaliação determinística.
Não conhece FastAPI, SQLAlchemy, arquivos, gabarito ou serviços externos.

As portas (`ports`) definem operações cadastrais/administrativas e execução do
worker. A aplicação (`application`) coordena essas portas e define erros comuns.
Adaptadores em `adapters` implementam HTTP, PostgreSQL, storage, ingestão,
serialização e coordenação transacional. A composição está em `http.py` e `cli.py`.
SQLAlchemy Core é usado para escritas/consultas em lote e tipos exatos; não há ORM
com objetos de 500 mil títulos carregados ao mesmo tempo.

As migrações Alembic têm SQL inicial congelado. A segunda migração adiciona
localização por arquivo/seq aos motivos, faz backfill e cria o índice de cursor
filtrado. Os DTOs monetários são strings e o domínio trabalha com Decimal 38.
O filtro por motivo limita a página no índice de motivos antes do join que busca
o JSON completo. Isso limita o trabalho mesmo enquanto as estatísticas do banco
ainda refletem menos linhas que os chunks recém-confirmados pelo worker.
Não existe leitura do gabarito em importadores, HTTP, worker ou motor.

O contrato JSON Schema canônico é usado pelo adaptador HTTP para validar tipos,
enums, unions, campos obrigatórios e extras. Regras semânticas adicionais seguem
o contrato em Markdown. O OpenAPI publicado é o contrato compartilhado; os testes
conferem o conjunto real de operationIds, as respostas emitidas e a regeneração
byte a byte dos artefatos. Não foram gerados DTOs alternativos incompatíveis.

Staging e resultados são separados. Checkpoints, resultados, títulos aprovados e
exposições são transacionais; diagnósticos são publicados junto ao batch ordenado.
O cursor autenticado fixa arquivo, filtros, limite, último item e teto disponível.
Os cursores auxiliares usam ordenação estável; histórico fixa um teto temporal.

Para simplificar concorrência, chunks do mesmo fundo são serializados por advisory
lock, incluindo suas raízes. É uma escolha conservadora de throughput, mantendo
unicidade entre fundos com locks adicionais por chave operacional e constraint
global. Não se promete o mesmo vencedor entre lotes concorrentes em execuções
diferentes. Esse custo está incluído nos benchmarks com um worker dedicado.
