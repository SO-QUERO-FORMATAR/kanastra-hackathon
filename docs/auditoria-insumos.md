# Auditoria dos quatro insumos

Leitura integral realizada em 24/10/2026, diretamente de `files/`, sem alterar os arquivos. O ZIP foi lido em memória, sem extração no repositório. Esta auditoria confere formato, correlação e invariantes; **não é execução do backend nem do motor completo**.

Reprodução: `python scripts/auditar_insumos.py`. Contagens detalhadas, PL por fundo, exemplos e hashes SHA-256 estão em [auditoria-insumos.json](auditoria-insumos.json).

| Verificação | Resultado |
|---|---|
| Conteúdo do ZIP | `estoque_antecipe.csv`, 20.276.472 bytes |
| Notas | 100.554, além do cabeçalho |
| Colunas | 11, conforme o contrato documentado |
| Fundos distintos | 18 |
| Fundos configurados no JSON | 1: ANTECIPE FIDC, CNPJ 92234400000180 |
| Validadores | 7 ativos e 2 inativos |
| Soma nominal de todos os fundos | R$ 604.931.711,69 |
| PL do ANTECIPE no estoque | R$ 53.074.028,00 |
| Base cadastral | 3.041 CNPJs distintos, sem repetição |
| Situações | 2.999 ATIVA, 22 INAPTA, 12 SUSPENSA, 8 BAIXADA |
| Gabarito | 100.554 itens; 85.215 APROVADO e 15.339 BARRADO |
| Correlação por linha/id | Completa, sem linhas extras, ausentes, repetidas ou IDs divergentes |
| Sacados sem cadastro | 1.406 documentos distintos, presentes em 22.222 linhas |
| Aprovados no gabarito com sacado ausente | 16.593 no conjunto; 712 pertencem ao ANTECIPE |
| Ocorrências de chave repetida após a primeira | 9.657 |
| Aprovações repetidas da mesma chave no gabarito | 4.941 ocorrências após a primeira aprovação |

Contagem de motivos no gabarito: TIPO_RECEBIVEL 9.842; PRAZO_MAXIMO 4.671; CONCENTRACAO_MAXIMA_SACADO 3.305; SITUACAO_CADASTRAL_SACADO 2.317; VALOR_MINIMO 34. Uma nota pode ter vários motivos; somar motivos não equivale a contar barrados. Não há `NOTA_DUPLICADA` no gabarito observado.

## Incompatibilidades comprováveis

**Configuração insuficiente:** o JSON identifica somente um fundo. Conforme decisão explícita do usuário, exigir configuração própria dos demais 17; não herdar nem replicar automaticamente as regras do ANTECIPE. A API precisa descobrir fundos, informar pendências, permitir configuração individual e retomar o lote.

**Base cadastral incompleta para as regras fornecidas:** a linha CSV 8, documento `526204`, do ANTECIPE, tem sacado `57.018.055/0001-46`, ausente da base, mas está APROVADO no gabarito. Com `SITUACAO_CADASTRAL_SACADO` ativa e ausência reprovando, essa aprovação não é compatível. Há 712 ocorrências desse tipo no fundo cuja configuração foi efetivamente fornecida; isso não depende de supor regras para os outros fundos.

**Duplicidade de aprovações:** as linhas 7371, 7372, 7373 e 7374 contêm a mesma chave operacional de cedente/sacado/documento `1-767495` no ANTECIPE e aparecem aprovadas. A regra obrigatória de unicidade impede essas aprovações posteriores. A comparação utilizou os documentos normalizados e o número textual, não apenas o número da nota.

**Concentração depende do estado inicial:** a linha 3 está barrada por concentração do sacado, embora seu nominal seja R$ 3.807,37 e o teto de 10% do PL do ANTECIPE seja R$ 5.307.402,80. Em estado inicial sem exposição anterior, somente as primeiras linhas não demonstram essa recusa. O estado anterior usado para gerar a referência precisa ser informado; não inferi-lo para forçar concordância.

## Consequência para a aceitação

Não é possível prometer correspondência integral com este gabarito mantendo simultaneamente todas as regras documentadas e esses dados de entrada. Não alterar os quatro arquivos originais nem remover testes de unicidade/cadastro para obter uma comparação verde.

O desenvolvimento e a integração front/back podem avançar com o contrato fechado e fixtures sintéticas consistentes. A aceitação oficial fica condicionada a configurações por fundo, correção/explicação das inconsistências e declaração do estado inicial. Eventual novo conjunto deve receber novos hashes e relatório de comparação; eventual mudança de regra deve ser explícita e refletida nos testes.
