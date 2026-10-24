# Antecipe — instalação e primeiros passos

O Antecipe recebe arquivos de recebíveis, aplica as regras de cada FIDC e apresenta aprovações, recusas, motivos e valores líquidos. Este tutorial mostra como executar o sistema localmente e fazer a primeira importação.

O projeto é dividido em:

- **Frontend:** Vue 3, Quasar, Vite e TypeScript, em `frontend/`.
- **Backend:** Python, FastAPI, PostgreSQL e worker de processamento, em `backend/`.
- **Arquivos compartilhados:** contratos em `docs/`, insumos em `files/` e ferramentas em `scripts/`.

O MVP local não exige login. A instalação abaixo usa a API real; o modo visual com dados simulados é opcional e está descrito ao final.

## 1. Instalar os pré-requisitos

Para executar todos os componentes em containers, instale:

| Ferramenta          | Windows e macOS                                                           | Linux                                                           |
| ------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Git                 | Git instalado e disponível no terminal                                    | Git instalado pelo gerenciador de pacotes                       |
| Docker + Compose v2 | Docker Desktop atualizado e em execução; no Windows, use containers Linux | Docker Engine em execução e plugin Docker Compose v2 atualizado |

Confira no terminal:

```sh
git --version
docker version
docker compose version
```

`docker version` deve mostrar tanto o cliente quanto o servidor. Se não houver conexão com o servidor, inicie o Docker antes de continuar.

Para a instalação com Docker, **não é necessário instalar Node.js, Python ou PostgreSQL no computador**. Será necessário acesso à internet no primeiro build para baixar imagens e dependências.

As portas locais **5173**, **8000** e **55432** devem estar disponíveis. Os comandos deste guia devem ser executados na raiz do repositório, salvo indicação contrária, e podem ser usados no PowerShell ou em um terminal Linux/macOS.

## 2. Baixar e conferir o projeto

Se ainda não tiver uma cópia:

```sh
git clone https://github.com/SO-QUERO-FORMATAR/kanastra-hackathon.git
cd kanastra-hackathon
```

Se já tiver o repositório, abra um terminal dentro dele. Use a branch que contém a integração do frontend e do backend. Antes de prosseguir, confira esta estrutura:

```text
kanastra-hackathon/
├── compose.yaml
├── compose.frontend.yaml
├── backend/
│   ├── Dockerfile
│   ├── init-test.sql
│   ├── antecipe/
│   └── README.md
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── files/
│   ├── cnpj_situacao_mock.csv
│   ├── validadores_antecipe.json
│   ├── estoque_antecipe_100k.zip
│   └── resultado_esperado_100k.json
├── docs/
└── scripts/
```

Se `frontend/` ou `compose.frontend.yaml` não aparecerem, sua cópia ainda não contém a integração. Atualize para a branch que inclui esses arquivos antes de seguir o tutorial.

Para a estrutura padrão acima, não é preciso criar um `.env`: o Compose já fornece a configuração local. Mantenha os nomes das pastas e dos arquivos de configuração.

## 3. Iniciar banco, API, worker e frontend

Na raiz, valide a configuração:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app config --quiet
```

Sem mensagem de erro, inicie os serviços:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app up --build -d
```

O primeiro build pode levar alguns minutos. O comando baixa as imagens, instala as dependências e inicia os cinco serviços:

| Serviço    | Função                             | Estado esperado após a inicialização |
| ---------- | ---------------------------------- | ------------------------------------ |
| `db`       | Banco PostgreSQL                   | Em execução e saudável (`healthy`)   |
| `migrate`  | Criação/atualização do schema      | Encerrado com sucesso (`Exited (0)`) |
| `api`      | API FastAPI e uploads              | Em execução e saudável               |
| `worker`   | Processamento assíncrono dos lotes | Em execução                          |
| `frontend` | Interface e proxy para a API       | Em execução e saudável               |

Consulte o estado:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app ps --all
```

Se um serviço ainda estiver em `starting`, aguarde e repita o comando. O serviço `migrate` encerrar com código zero é normal; ele executa uma tarefa única. Já `Exited` com código diferente de zero indica uma falha que deve ser investigada nos logs.

A sequência de inicialização é banco → migrações → API/worker → frontend. O perfil `app` e os dois argumentos `-f` são necessários para subir o sistema completo.

## 4. Carregar a base cadastral e as regras iniciais

Com a API saudável, execute estes comandos **uma vez na instalação inicial**:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app exec api python -m antecipe.cli import-registry /inputs/cnpj_situacao_mock.csv

docker compose -f compose.yaml -f compose.frontend.yaml --profile app exec api python -m antecipe.cli import-rules /inputs/validadores_antecipe.json
```

O primeiro comando retorna um JSON com `versao_cadastral`. O segundo retorna `fundo_id` e `versao`. Esses resultados identificam as cargas persistidas no banco.

O caminho `/inputs` existe dentro do container e corresponde à pasta `files/` do seu computador. Não substitua esse caminho por `files/` nos comandos de `exec`.

A base cadastral fornecida é de demonstração. A carga de regras configura **somente o ANTECIPE FIDC**; ela não configura os demais fundos automaticamente. Não envie o CSV cadastral nem o JSON de regras pela tela de upload de recebíveis.

Reimportar a mesma base é idempotente. Substituir uma base por outra enquanto houver lotes que a utilizam pode ser recusado; consulte o [guia do backend](backend/README.md) antes de alterar cargas de uma instalação em uso.

## 5. Abrir o sistema

No navegador do seu computador, abra o endereço indicado:

| Recurso                        | Endereço local                                 |
| ------------------------------ | ---------------------------------------------- |
| Interface do Antecipe          | `http://localhost:5173`                        |
| Documentação interativa da API | `http://localhost:8000/docs`                   |
| Saúde da API                   | `http://localhost:8000/api/v1/health/ready`    |
| Situação da base cadastral     | `http://localhost:8000/api/v1/cadastro/status` |

Na consulta cadastral, `disponivel` deve ser `true` após a carga. O endpoint de saúde pode estar saudável mesmo sem base cadastral; por isso, verifique ambos.

Na interface, o cabeçalho deve indicar **Ambiente de integração**. Se aparecer **Demonstração · dados de exemplo**, você está usando o modo simulado de desenvolvimento, não o frontend definido neste Compose.

A interface encaminha `/api/v1` para a API pela rede Docker. Você não precisa configurar manualmente uma URL de backend no navegador.

## 6. Fazer a primeira importação

### Preparar o arquivo

Para usar o conjunto fornecido:

1. Localize `files/estoque_antecipe_100k.zip` no computador.
2. Use **Extrair tudo** ou a ferramenta de descompactação do seu sistema.
3. Localize o arquivo extraído `estoque_antecipe.csv`.

**Selecione o CSV extraído, não o ZIP.** `resultado_esperado_100k.json` é uma referência de auditoria e também não deve ser enviado como recebível.

O conjunto completo contém 100.554 notas de 18 fundos. É esperado que esse lote fique bloqueado enquanto faltarem as configurações dos outros 17 fundos; esse estado não indica, por si só, uma falha de instalação.

Para usar arquivos próprios:

- Formatos aceitos: `.csv` e `.xlsx`; até 100 arquivos e 500.000 linhas de dados por lote.
- Limite publicado pelo MVP: 64 MiB por arquivo e por batch. A interface organiza os batches automaticamente.
- CSV: UTF-8, delimitador `;`, valores no formato brasileiro (por exemplo, `10000,00`) e datas em `dd/mm/aaaa`.
- XLSX: cabeçalho na primeira linha; o upload da interface usa a primeira aba com dados. Preserve CNPJs e números de documentos como texto para manter os zeros iniciais.

O cabeçalho deve conter as onze colunas obrigatórias:

```text
NOME_FUNDO;DOC_FUNDO;NOME_CEDENTE;DOC_CEDENTE;NOME_SACADO;DOC_SACADO;NU_DOCUMENTO;TIPO_RECEBIVEL;VALOR_NOMINAL;DATA_VENCIMENTO_ORIGINAL;DATA_AQUISICAO
```

### Enviar e iniciar a análise

1. Na **Visão geral**, clique em **Nova importação**, ou abra **Importar recebíveis** no menu.
2. Preencha **Nome do lote**, por exemplo, `Primeira importação`.
3. Clique em **Selecionar arquivos** ou arraste os arquivos para a área de upload.
4. Confira a seleção e clique em **Enviar recebíveis**.
5. Aguarde a confirmação do envio. A interface abrirá o acompanhamento do lote.
6. Clique em **Iniciar análise**.

O envio confirmado não significa aprovação financeira. O worker primeiro prepara os dados, verifica os pré-requisitos e depois executa a análise.

Se o envio for interrompido, use **Retomar envio**. Se tiver recarregado a página, selecione os mesmos arquivos na mesma ordem. Para alterar o conteúdo ou a seleção, use **Nova seleção**, criando outro manifesto.

## 7. Resolver pendências e consultar resultados

No acompanhamento, observe o status do lote:

| Status                               | Significado e próximo passo                                                       |
| ------------------------------------ | --------------------------------------------------------------------------------- |
| `RECEBENDO`                          | Conclua o envio dos arquivos e inicie a análise quando a ação estiver disponível. |
| `NA_FILA`, `INDEXANDO`, `ANALISANDO` | O processamento está em andamento; acompanhe os contadores.                       |
| `BLOQUEADO`                          | Leia as pendências e execute a ação indicada antes de retomar.                    |
| `CONCLUIDO`                          | O processamento terminou; consulte os resultados.                                 |
| `CONCLUIDO_COM_ERROS`                | Há resultados disponíveis, mas também erros de dados ou de estrutura a verificar. |
| `FALHOU`                             | Consulte a mensagem; retome somente se a interface oferecer essa ação.            |

### Fundo sem regras

1. Na pendência, clique em **Configurar fundo**.
2. Em **Fundos e regras**, revise os nove validadores, seus parâmetros e a precificação do fundo selecionado.
3. Preencha também os parâmetros dos validadores inativos; eles precisam ser válidos para salvar a configuração.
4. Marque **Revisei os nove validadores e a precificação deste fundo.**
5. Clique em **Salvar configuração**.
6. Repita para cada fundo pendente, usando critérios definidos para aquele fundo.
7. Volte ao lote pelo histórico e clique em **Retomar análise**.

As regras do ANTECIPE não devem ser copiadas automaticamente para os outros fundos. Se outra pessoa tiver alterado a versão durante sua edição, use **Recarregar configuração** e revise antes de salvar novamente.

### Outras pendências

- **Base cadastral ausente:** realize a carga administrativa do passo 4 e retome o lote.
- **Dados que impedem calcular o PL:** corrija o arquivo original e faça uma nova importação. Os arquivos de um lote já criado são imutáveis.

### Ler os resultados

Selecione um arquivo em **Arquivo para consulta** e examine a tabela **Resultados da análise**:

- **Aprovado:** recebível elegível, com desconto e valor líquido retornados pelo backend.
- **Barrado:** recusa financeira normal; abra o detalhe para consultar todos os motivos.
- **Erro de dados:** diagnóstico de ingestão, como data inválida. Consulte os campos originais e a linha de origem.

Use os filtros de resultado e motivo, os botões anterior/próxima e a ação de detalhe de cada linha. Durante o processamento, **Atualizar** busca os resultados mais recentes. Os cards mostram os totais do lote, não apenas os itens visíveis na página.

## 8. Parar e voltar a usar

Para parar os serviços preservando o banco, o histórico e os arquivos recebidos:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app down
```

Para iniciar novamente, sem reconstruir imagens que não mudaram:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app up -d
```

As cargas iniciais permanecem nos volumes; não é necessário repeti-las a cada início. Após atualizar código ou dependências, use novamente `up --build -d`.

Não acrescente `-v` ao comando `down` para uma instalação cujo histórico deseja manter: essa opção remove os volumes de dados. O nome e a localização do projeto influenciam os nomes dos volumes usados pelo Compose; mantenha a mesma pasta para reutilizar sua instalação.

## 9. Solucionar problemas comuns

Para ver os logs:

```sh
docker compose -f compose.yaml -f compose.frontend.yaml --profile app logs --tail 100 api worker frontend
```

Para acompanhar continuamente, acrescente `-f` após `logs`. `Ctrl+C` encerra apenas o acompanhamento dos logs.

| Problema                             | O que verificar                                                                                                                           |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Docker não conecta ao servidor       | Abra o Docker Desktop ou inicie o Docker Engine; repita `docker version`.                                                                 |
| Porta já está em uso                 | Pare a instância anterior ou o processo que ocupa 5173, 8000 ou 55432. Não execute Vite no host e o frontend em container na mesma porta. |
| Arquivo ou Dockerfile não encontrado | Confirme a estrutura do passo 2 e execute os comandos na raiz, não dentro de `frontend/` ou `backend/`.                                   |
| Download de imagem/pacote falha      | Verifique internet, DNS e configuração de proxy do Docker; após corrigir, repita `up --build -d`.                                         |
| API não fica saudável                | Consulte `logs --tail 100 db migrate api`; `migrate` deve concluir com código zero.                                                       |
| Interface abre, mas não obtém dados  | Verifique o estado de `api` e `frontend`, e os logs dos dois serviços.                                                                    |
| Lote fica na fila                    | Confirme que `worker` está em execução e consulte seus logs.                                                                              |
| Base cadastral ausente               | Execute `import-registry` conforme o passo 4 e consulte `/api/v1/cadastro/status`.                                                        |
| Fundo sem configuração               | Configure cada fundo pendente e retome explicitamente a análise.                                                                          |
| Nota repetida aparece como barrada   | Uma nota aprovada em um lote anterior pode ser recusada como duplicada em um novo lote; consulte o motivo apresentado.                    |

Se você tiver Node.js 24 e as dependências do frontend instaladas, pode verificar os quatro endpoints de diagnóstico através do proxy:

```sh
npm --prefix frontend ci
npm --prefix frontend run api:check
```

Esse comando verifica saúde, capacidades e cadastro conforme o contrato. Ele não substitui uma importação completa.

## 10. Desenvolvimento e testes — opcional

### Editar o frontend com Vite no computador

Instale Node.js 24 e npm. Use apenas o Compose do backend para deixar a porta 5173 livre:

```sh
docker compose --profile app up --build -d
cd frontend
npm ci
```

Copie `frontend/.env.example` para `frontend/.env.local` pelo gerenciador de arquivos. Os valores padrão já são:

```dotenv
VITE_API_BASE_URL=/api/v1
API_PROXY_TARGET=http://127.0.0.1:8000
VITE_DEMO_MODE=false
```

Dentro de `frontend/`, inicie:

```sh
npm run dev -- --port 5173 --strictPort
```

As cargas do passo 4 continuam necessárias na primeira instalação. Para visualizar somente a interface, sem backend, altere `VITE_DEMO_MODE=true` em `.env.local` e reinicie o Vite. Esse modo exibe exemplos fixos, não analisa o conteúdo dos arquivos e reinicia seu estado simulado ao recarregar a página. Volte para `false` para usar a API real.

### Validar o frontend

Na raiz, com suas dependências instaladas:

```sh
npm --prefix frontend run check:api
npm --prefix frontend test
npm --prefix frontend run build
```

Para testes no navegador, entre em `frontend/`:

```sh
npx playwright install chromium
npm run test:e2e
```

Os testes iniciam seus próprios servidores; as portas 5173 e 5174 devem estar livres. Eles validam a interface com respostas controladas e não certificam o backend real.

Para desenvolver e testar o backend com Python 3.13.5 e `uv`, siga [backend/README.md](backend/README.md). As suítes de backend recriam o schema do banco `antecipe_test`; use a configuração de teste documentada e não execute as suítes em paralelo contra esse banco.

## Limites da demonstração e documentação adicional

O conjunto fornecido tem inconsistências conhecidas no gabarito e configurações pendentes para 17 fundos. O arquivo `resultado_esperado_100k.json` é usado para auditoria, não para determinar as decisões da aplicação. A aceitação completa desse conjunto continua condicionada às pendências registradas nos documentos do backend.

- [Guia e comandos do backend](backend/README.md).
- [Guia técnico do frontend](frontend/README.md) e [opções de execução local](frontend/docs/local-development.md).
- [Contrato de integração HTTP](docs/contrato-api.md) e [OpenAPI canônico](docs/contratos/openapi.json).
- [DTOs](docs/contratos/dtos.md), [tipos TypeScript compartilhados](docs/contratos/api-types.ts) e [exemplos](docs/contratos/exemplos.json).
- [Planejamento do backend](docs/planejamento-backend.md) e [evidências de aceitação](docs/execucao/checklist.md).
- [Auditoria dos insumos](docs/auditoria-insumos.md) e [referência de integração do frontend](docs/handoff-frontend.md).

Os geradores compartilhados ficam em `scripts/`: `python scripts/gerar_contrato_api.py`, `python scripts/auditar_insumos.py` e `python scripts/validar_contrato_api.py` (este último utiliza `scripts/requirements-contratos.txt`). Alterações de contrato devem ser coordenadas entre backend e frontend; `check:api` verifica a igualdade das cópias e a atualização dos tipos da interface.
