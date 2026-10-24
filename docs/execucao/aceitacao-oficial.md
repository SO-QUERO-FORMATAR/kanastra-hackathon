# Aceitação oficial — pendente

O CSV oficial foi enviado pela API, persistido no storage e indexado pelo worker
com PostgreSQL 16.15 real. Os quatro arquivos de entrada não foram modificados.

- 100.554 linhas indexadas, 18 fundos descobertos.
- PL total: `604931711.69`; PL do ANTECIPE: `53074028.00`.
- 17 pendências `FUNDO_SEM_REGRAS`; status final da tentativa: `BLOQUEADO`.
- Zero resultados financeiros publicados e zero aprovações reservadas.
- Indexação medida na repetição final: 19,630 segundos.

[Relatório de execução e comparação](aceitacao-oficial.json) inclui lote, PL de
cada fundo, pendências, contexto e as 100.554 linhas ainda sem decisão. Ausência
de decisão por bloqueio não equivale a recusa calculada nem divergência financeira.

[Contradições por linha](divergencias-referencia.jsonl) registra 4.941 aprovações
repetidas da mesma chave operacional e 712 aprovações do ANTECIPE com sacado
ausente da base. Cada registro contém arquivo, linha, número textual, fundo,
regra, hashes de configuração/cadastro e indicação de estado inicial não fornecido.
São verificações independentes do gabarito, sem modificar o estado do motor.

Para concluir a aceitação, fornecer regras próprias dos 17 fundos, reconciliar
cadastro/gabarito e declarar o histórico inicial de aprovações/exposições. O
comparador normaliza ausência de motivos em aprovado como lista vazia e detecta
faltantes, extras, IDs divergentes, motivos/status divergentes e linhas repetidas.
Ele recebe resultados por arquivo e correlaciona pela linha física e número textual.

Reprodução: `uv run --directory backend python -m antecipe.acceptance.official`
e `uv run --directory backend python -m antecipe.acceptance.audit`.
O primeiro comando recria exclusivamente `antecipe_test`; não executar junto
com a suíte ou benchmarks. O segundo é somente leitura dos insumos e escrita
do relatório. Nenhum código de decisão importa o pacote `acceptance`.
