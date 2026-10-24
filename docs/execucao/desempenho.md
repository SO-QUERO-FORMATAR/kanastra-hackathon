# Volumetria e consultas

Medições com PostgreSQL 16.15 real em Docker, API Uvicorn em TCP local e worker
em outro processo. O gerador usa documentos textuais, números únicos, Decimal,
um fundo sintético com configuração própria e uma recusa a cada dez linhas.
Nenhum gabarito oficial participa desses ensaios.

| Conjunto | Tempo do worker (duas passagens) | Pico RSS da árvore do worker | p95 agregado | Meta por filtro |
|---|---:|---:|---:|---|
| 100.000 CSV | 81,961 s | 106.340.352 bytes (101,4 MiB) | 57,729 ms | Atendida |
| 500.000 XLSX, dois arquivos | 740,434 s (12min20s) | 142.295.040 bytes (135,7 MiB) | 46,345 ms | Atendida |

O relógio começa após manifesto/upload, antes de iniciar o worker; geração de
arquivos e transferência não estão incluídas no tempo de processamento.
Contagens, nominal, desconto e líquido são comparados com valores sintéticos
esperados antes de o benchmark declarar sucesso. A conclusão exige p95 ≤ 300 ms
**em cada filtro**, sem timeouts, para páginas de 100 resultados.

O ensaio CSV confirmou 90.000 aprovações e 10.000 barramentos, nominal
`10001000.00`, desconto `180000.00` e líquido `8820900.00`. Houve 50 consultas
cadastrais para 50 chunks de 2.000 títulos, sempre por documentos distintos.

O XLSX confirmou 450.000 aprovações e 50.000 barramentos, nominal `50005000.00`,
desconto `900000.00` e líquido `44104500.00`. Houve 250 consultas cadastrais para
250 chunks, com 2.514 statements de escrita e 4.292 statements totais no worker.

| Filtro | p95 CSV 100k, ms | p95 XLSX 500k, ms |
|---|---:|---:|
| Sem filtro | 96,812 | 44,178 |
| APROVADO | 28,543 | 54,753 |
| BARRADO | 29,982 | 45,078 |
| Motivo TIPO_RECEBIVEL | 32,411 | 46,100 |
| Tipo ERRO_DADOS | 23,255 | 32,352 |

O filtro ERRO_DADOS é vazio nessa massa; o comportamento com diagnósticos e
múltiplos motivos é coberto na regressão funcional. A carga concorrente medida
é um worker e um cliente de consultas, sem prometer desempenho para concorrências
maiores. A API/worker da instalação Compose ficaram ociosos no segundo ensaio XLSX.

[Ambiente e método](ambiente-volume.json) registra CPU, memória, recursos do
Docker, aquecimento, amostragem e concorrência. [Índices](indices-postgresql.txt)
registra as definições SQL. Os JSONs de volume contêm todas as amostras, separadas
por filtro e fase, somas, contadores SQL e informações do host. Após aquecer uma
vez cada filtro, são coletadas 100 amostras no conjunto concluído, além das
amostras durante a análise com snapshot não vazio. O p95 usa o índice
`floor(0,95 × (n − 1))` do vetor ordenado.

## Otimizações e ensaios anteriores

- Listas grandes de pares em `IN` foram substituídas por joins com `VALUES` nas
  consultas de origem e chave operacional; isso reduziu o tempo do CSV de cerca
  de 170 s para cerca de 82 s no mesmo ambiente.
- A migração 0002 adicionou localização por arquivo/sequência e índice coberto
  aos motivos. O primeiro XLSX completo ainda falhou a meta: p95 de motivo de
  498,996 ms, apesar de p95 agregado de 58,217 ms e somas corretas.
- A consulta passou a limitar os motivos antes do join que busca o JSON dos
  resultados, evitando trabalho proporcional à tabela durante atualização de
  estatísticas. A regressão funcional passou antes da repetição dos volumes.

`volume-100000-csv-baseline.json` é um diagnóstico antigo: seu RSS mede somente
o launcher do Windows e seu sucesso considerava p95 agregado. **Não usar esses
campos como evidência de memória ou da meta final.**
`volume-500000-xlsx-before-page-bound.json` preserva o ensaio que falhou a meta
por filtro. Os arquivos sem esses sufixos representam as medições mais recentes.

Não há SLA de tempo total ou teto de RAM no contrato. Os picos observados são
orçamento medido nesse host, não garantia universal. A leitura XLSX em streaming
e os chunks evitam manter 500 mil títulos Python simultaneamente.

Reproduzir, sem suíte simultânea no banco `antecipe_test`:

```powershell
uv run --directory backend python -m antecipe.performance.benchmark --count 100000 --format CSV
uv run --directory backend python -m antecipe.performance.benchmark --count 500000 --format XLSX
```
