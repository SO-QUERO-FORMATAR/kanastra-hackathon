"""Empacota contrato e exemplos num prompt que não depende do repositório."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gerar_handoff():
    contracts = ROOT / "docs" / "contratos"
    spec = json.loads((contracts / "openapi.json").read_text(encoding="utf-8"))
    scenarios = json.loads((contracts / "exemplos.json").read_text(encoding="utf-8"))
    schemas = spec["components"]["schemas"]
    seeds = {example["schema"]: example["valor"] for example in scenarios["exemplos"]}
    named = {example["nome"]: example["valor"] for example in scenarios["exemplos"]}
    seeds.update({
        "FundoDTO": named["regras_publicadas"]["fundo"],
        "ArquivoDTO": named["lote_criado"]["arquivos"][0],
        "ConfiguracaoRegrasDTO": named["configurar_fundo"]["configuracao"],
        "PrecificacaoDTO": named["configurar_fundo"]["configuracao"]["precificacao"],
        "ErroDTO": named["erro_versao"]["erro"],
        "PendenciaDTO": named["pendencias"]["itens"][0],
        "ImportarRegrasRequest": {"fundo": {"nome": named["regras_publicadas"]["fundo"]["nome"], "cnpj": named["regras_publicadas"]["fundo"]["cnpj"]}, **named["configurar_fundo"]["configuracao"]},
        "EnviarBatchRequest": {"metadados": json.dumps(named["metadados_batch"], separators=(",", ":")), "arquivos": ["<bytes do arquivo; parte binaria multipart>"]},
    })
    for name, item in zip(["ResultadoAprovadoDTO", "ResultadoBarradoDTO", "ResultadoErroDadosDTO"], named["resultados"]["itens"]):
        seeds[name] = item
    seeds["TituloNormalizadoDTO"] = seeds["ResultadoAprovadoDTO"]["titulo"]
    seeds["DadosOriginaisTituloDTO"] = seeds["ResultadoAprovadoDTO"]["dados_originais"]
    seeds["MotivoDTO"] = seeds["ResultadoBarradoDTO"]["motivos"][0]
    seeds["ErroDadoDTO"] = seeds["ResultadoErroDadosDTO"]["erros_dados"][0]
    for rule in seeds["ConfiguracaoRegrasDTO"]["validadores"]:
        name = schemas["ValidadorDTO"]["discriminator"]["mapping"][rule["codigo"]].split("/")[-1]
        seeds[name] = rule
        params_name = schemas[name]["allOf"][0]["then"]["properties"]["parametros"]["$ref"].split("/")[-1]
        seeds.setdefault(params_name, rule["parametros"])

    counter = 100

    def sample(schema):
        nonlocal counter
        if "$ref" in schema:
            name = schema["$ref"].split("/")[-1]
            return seeds[name] if name in seeds else sample(schemas[name])
        if "enum" in schema:
            return schema["enum"][0]
        if "default" in schema:
            return schema["default"]
        if "examples" in schema:
            return schema["examples"][0]
        if "oneOf" in schema or "anyOf" in schema:
            return sample(schema.get("oneOf", schema.get("anyOf"))[0])
        kind = schema.get("type")
        if kind == "object":
            return {key: sample(value) for key, value in schema.get("properties", {}).items()
                    if key in schema.get("required", []) or "default" in value}
        if kind == "array":
            count = schema.get("minItems", 0 if schema.get("maxItems") == 0 else 1)
            return [sample(schema["items"]) for _ in range(count)]
        if kind == "null":
            return None
        if kind == "boolean":
            return False
        if kind in ("integer", "number"):
            return schema.get("minimum", 0)
        if kind == "string":
            fmt = schema.get("format")
            if fmt == "uuid":
                counter += 1
                return f"00000000-0000-4000-8000-{counter:012d}"
            if fmt == "date":
                return "2026-10-24"
            if fmt == "date-time":
                return "2026-10-24T18:00:00Z"
            if fmt == "uri-reference":
                return "/api/v1/lotes/00000000-0000-4000-8000-000000000012"
            pattern = schema.get("pattern")
            if pattern == r"^[0-9]{14}$":
                return "92234400000180"
            if pattern == r"^[0-9]{8}$":
                return "92234400"
            if pattern == r"^[a-f0-9]{64}$":
                return "a" * 64
            return "exemplo"
        raise ValueError(f"Schema não suportado: {schema}")

    payloads = {name: seeds[name] if name in seeds else sample(schema) for name, schema in schemas.items()}
    # Examples of independent list/summary DTOs must also obey business invariants.
    payloads["ProgressoDTO"] = named["lote_criado"]["lote"]["progresso"]
    payloads["ResumoFinanceiroDTO"] = named["lote_criado"]["lote"]["resumo"]
    payloads["AcoesLoteDTO"] = named["lote_criado"]["lote"]["acoes"]
    initial_lot = named["lote_criado"]["lote"]
    payloads["LoteResumoDTO"] = {
        **{key: initial_lot[key] for key in ["id", "nome", "status", "criado_em", "atualizado_em"]},
        "arquivos_total": 1, "linhas_processadas": 0, "total_liquido": "0.00",
    }
    payloads["LotesPageResponse"]["itens"] = [payloads["LoteResumoDTO"]]
    payloads["ResumoFundoDTO"] = {
        "fundo": seeds["FundoDTO"], "versao_regras_utilizada": None,
        "pl": "0.00", "limite_sacado": None, "limite_cedente": None,
        "resumo": payloads["ResumoFinanceiroDTO"],
    }
    payloads["ResumosFundosPageResponse"] = {"itens": [payloads["ResumoFundoDTO"]], "proximo_cursor": None, "limit": 50}
    for name in ["FundosPageResponse", "LotesPageResponse", "ArquivosPageResponse"]:
        payloads[name]["proximo_cursor"] = None
        payloads[name]["limit"] = 50

    prose = (ROOT / "docs" / "contrato-api.md").read_text(encoding="utf-8")
    prose = prose.split("## Convenções gerais", 1)[1].split("## Limitação da aceitação oficial", 1)[0]
    prose = "## Convenções gerais" + prose
    prose = prose.replace("contrato-api.md", "contrato incluído neste prompt")
    prefix = """# Prompt autocontido para planejar o frontend Antecipe

Copie TODO este documento para o outro contexto, ou anexe somente este arquivo. Ele contém o contrato completo: não é necessário ter acesso ao repositório, aos outros documentos ou à conversa anterior. O conteúdo entre os marcadores abaixo é o prompt.

<!-- INICIO DO PROMPT -->

Você vai planejar o frontend do Antecipe em Vue 3 + Quasar com TypeScript. O Antecipe recebe notas/recebíveis CSV ou XLSX, processa regras de FIDC no backend e apresenta aprovações, recusas, motivos e valores líquidos.

Quero um planejamento sequencial de implementação do frontend. Para cada tarefa, descreva objetivo, dependências, tela/componentes, operação HTTP, DTOs de request/response, testes novos, regressão acumulada e critério de conclusão. Comece pelos tipos e cliente da API, depois mocks, seleção/upload, acompanhamento e pendências, configuração de regras, resumos, histórico e tabela de resultados. Finalize com testes de contrato e integração real. Não considere nenhuma funcionalidade já implementada.

Este prompt é a fonte completa do contrato v1.0.0. Não peça para ler arquivos locais nem dependa do chat anterior. Gere os tipos TypeScript a partir do OpenAPI incluído aqui; não invente endpoints, campos, enums, autenticação ou paginação por offset. Os schemas são normativos; os exemplos são ilustrativos e não substituem obrigatoriedade, tipos ou validações. Se identificar uma incompatibilidade, registre-a antes de propor qualquer mudança coordenada no contrato.

## Entrega esperada do planejamento

1. Mapa de telas e navegação, estados de carregamento, erro, vazio, bloqueio e sucesso.
2. Estrutura do projeto, componentes, cliente HTTP, stores/composables e tipos derivados do contrato.
3. Tarefas em ordem de execução com testes a cada etapa e regressão antes de avançar.
4. Matriz tela/ação → operationId → request → response → erros → testes.
5. Estratégia de mocks usando os JSONs abaixo, seguida de validação contra a API real quando disponível.
6. Checklist final de compatibilidade: multipart, idempotência, dinheiro em string, versionamento, polling, retomada e cursores.

## Contexto confirmado

- Backend planejado: Python/FastAPI/PostgreSQL, processamento assíncrono em duas passagens. Ainda não implementado.
- Há 100.554 notas de 18 fundos no dataset; só o ANTECIPE FIDC possui regras fornecidas.
- Decisão do usuário: cada fundo exige configuração própria. Não copiar regras automaticamente para os outros 17. A interface deve informar e resolver as pendências.
- A base cadastral é importada em tabela PostgreSQL por operação administrativa, não por upload de notas no navegador.
- O gabarito contém inconsistências: 712 aprovações do ANTECIPE sem cadastro do sacado e 4.941 aprovações repetidas de chaves no conjunto. Não tratar esse gabarito como execução certificada nem usá-lo como fonte de decisões da interface.
- O frontend pode ser planejado e testado sem esses arquivos. Todas as DTOs necessárias estão neste documento.
- Não implementar login, exportação, cancelamento, edição de decisão, upload do gabarito ou importação cadastral no navegador: não há contrato para essas funções no MVP.

"""
    # One object per line keeps the complete JSON compact without dropping fields.
    compact = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    spec_lines = []
    for key, value in spec.items():
        if key == "paths":
            content = "{\n" + ",\n".join(f"  {json.dumps(path)}: {compact(methods)}" for path, methods in value.items()) + "\n}"
        elif key == "components":
            content = '{"schemas":{\n' + ",\n".join(f"  {json.dumps(name)}: {compact(schema)}" for name, schema in schemas.items()) + "\n}}"
        else:
            content = compact(value)
        spec_lines.append(f"  {json.dumps(key)}: {content}")
    openapi_json = "{\n" + ",\n".join(spec_lines) + "\n}"
    examples_json = "{\n" + ",\n".join(f"  {json.dumps(name)}: {compact(value)}" for name, value in payloads.items()) + "\n}"
    output = prefix + prose + """
## OpenAPI completo — todas as operações e todos os schemas de DTO

O bloco abaixo é JSON válido e autocontido. Os `$ref` são referências internas ao próprio bloco (`#/components/schemas/...`), não a arquivos externos. Os DTOs de query, corpos de request, responses, erros, enums e variantes estão todos em `components.schemas`. Não omitir propriedades ao gerar os tipos. Campos opcionais e campos `null` são conceitos diferentes.

```json
""" + openapi_json + "\n```\n\n" + """## Exemplos JSON de todos os schemas

Há uma entrada por schema do contrato, incluindo tipos escalares, enums, objetos auxiliares, DTOs de query, requests, responses e variantes discriminadas. Estes são exemplos de forma e de cenários independentes: IDs não precisam representar uma única execução coerente entre entradas. As strings de cursor são ilustrativas e não podem ser usadas como cursores reais do servidor. Os exemplos não dispensam as restrições semânticas descritas acima.

`EnviarBatchRequest` é a única representação de transporte multipart: seu campo `arquivos` contém placeholders descritivos de bytes, não strings para enviar como JSON. Use FormData e arquivos binários reais, seguindo a seção de multipart. Queries viram parâmetros de URL, nunca corpos JSON. POST de processamento não tem corpo.

```json
""" + examples_json + "\n```\n\n" + """## Fixtures detalhadas dos fluxos principais

Estes cenários complementam os exemplos por DTO. O arquivo/hash fictício não corresponde a bytes disponíveis: para testar upload real, gerar um arquivo e calcular seu hash/tamanho. O bloco contém criação, upload, fila, bloqueio, configuração, resultados e erro de versão.

```json
""" + json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n```\n\n" + """## Antes de concluir o planejamento

Verifique que toda ação planejada usa uma das operações acima; nenhum cálculo decisório foi transferido ao frontend; cada tarefa possui testes; e o fluxo cobre fundos não configurados, retry sem duplicação, conflito de versão, leitura por cursor e erro de dados separado de recusa financeira. Não é necessário solicitar nenhum outro arquivo para elaborar esse plano.

<!-- FIM DO PROMPT -->
"""
    target = ROOT / "docs" / "handoff-frontend.md"
    target.write_text(output, encoding="utf-8")
    print(f"Prompt autocontido gerado: {len(schemas)} schemas e {len(payloads)} exemplos de DTOs; {len(output)} caracteres.")


if __name__ == "__main__":
    gerar_handoff()
