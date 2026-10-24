# Guia de Estilo e Diretrizes de UX/UI — Padrão Fintech B2B (Inspirado em Kanastra)

Este documento sintetiza as diretrizes visuais, a paleta de cores, a tipografia e os princípios de experiência do usuário para o desenvolvimento de uma interface institucional, moderna e voltada ao mercado de mercado de crédito estruturado e gestão de FIDCs.

---

## 1. Conceito Visual e Posicionamento (Brand Identity)

- **Estilo:** _Institutional Fintech / B2B Credit Infrastructure_.
- **Sensação Esperada:** Solidez bancária com modernidade tecnológica, transparência e sofisticação.
- **Diferencial:** Foge do tom azul corporativo tradicional. Utiliza variações profundas de verde com superfícies quentes (off-white/creme), criando um contraste elegante e reduzindo o cansaço visual.

---

## 2. Paleta de Cores (Color Tokens)

### 2.1. Cores Principais

- **Verde Institucional (`#193C32`):**
  - _Uso:_ Header, navegação, cards de destaque primário, botões principais e títulos de alto impacto.
- **Verde Tech 1 (`#1E5546`):**
  - _Uso:_ Hover de botões, estados ativos de menus e bordas de destaque.
- **Verde Tech 2 (`#14735A`):**
  - _Uso:_ Badges de aprovação, métricas de crescimento, elementos numéricos de destaque e ícones ativos.

### 2.2. Superfícies e Fundos (Backgrounds)

- **Fundo Creme Quente (`#F8F1E0`):**
  - _Uso:_ Cor de fundo da aplicação e das páginas principais. Traz aconchego visual e sobriedade.
- **Branco Puro (`#FFFFFF`):**
  - _Uso:_ Fundo dos cards, tabelas de dados, modais e formulários. Cria um contraste limpo e modular sobre o fundo creme.

### 2.3. Cores de Status e Feedback Operacional

- **Status Aprovado:** Fundo verde claro com texto em Verde Tech 2 (`#14735A`).
- **Status Barrado / Recusado:** Fundo vermelho/vinho suave (`#FDE8E8`) com texto escuro (`#9B1C1C`).
- **Status Pendente / Alerta:** Fundo âmbar/amarelo suave (`#FEF3C7`) com texto escuro (`#92400E`).

---

## 3. Tipografia e Hierarquia Visual

A hierarquia tipográfica combina uma fonte de títulos com caracteres estendidos/geométricos e uma fonte corporativa ultralegível para densidade de dados.

### 3.1. Famílias Tipográficas

1. **Títulos e Números de Impacto (KPIs):** _Sans-serif Estendida / Geometric Light_ (Exemplos equivalentes: `Vinila Extended`, `Syne`, `Space Grotesk` ou `Montserrat Wide`).
2. **Subtítulos e Interface (UI Labels):** _Sans-serif Medium_ (Exemplos: `Inter Display`, `Plus Jakarta Sans`).
3. **Corpo de Texto e Tabelas:** _Sans-serif Clean_ (Exemplo: `Inter`).

### 3.2. Hierarquia de Aplicação

- **H1 / Capa:** Caixa alta/baixa, peso leve ou médio, tamanho amplo.
- **KPIs / Números do Fundo:** Valor numérico em fonte estendida, acompanhado de uma legenda pequena em caixa alta (`UPPERCASE`).
- **Tabelas de Dados:** Fonte regular de alta legibilidade em tamanho reduzido (13px a 14px), garantindo alta densidade de informação sem poluição visual.

---

## 4. Componentes de UI (UI Component Patterns)

### 4.1. Cards e Módulos de Informação

- **Bordas:** Suaves e arredondadas (`border-radius: 8px` a `12px`).
- **Sombra (Elevation):** Mínima ou nula. A separação dos elementos é feita por diferença de cor de fundo (card branco sobre fundo creme) e bordas finas sutis (`1px solid #E5E7EB`).
- **Padding:** Espaçamento interno generoso em cards de topo (`20px` a `24px`) e mais enxuto em células de tabelas.

### 4.2. Tabelas de Recebíveis (Esteira de Validação)

- **Cabeçalho:** Fundo sutil, texto em caixa alta e tom escuro/médio.
- **Linhas de Dados:** Alternância sutil de cor ou linhas divisórias finas.
- **Badges de Motivo de Barrado:** Tags arredondadas (`pill badges`) com cores associadas a cada tipo de regra/alerta.
- **Valores Monetários:** Alinhados à direita com alinhamento numérico legível.

### 4.3. Filtros e Barras de Busca

- Inputs de busca e seletores limpos com borda fina e foco no tom Verde Tech.
- Botões primários em bloco sólido no tom Verde Institucional (`#193C32`) com texto claro.

---

## 5. Princípios de Experiência do Usuário (UX)

1. **Redução da Fadiga Visual:** O uso de superfícies quentes (off-white) em vez do branco brilhante reduz o cansaço em análises prolongadas de relatórios e esteiras de risco.
2. **Arquitetura "Data-Dense":** Telas financeiras B2B exigem visualização rápida de grandes volumes de informação. Os dados são dispostos de forma enxuta, mantendo o espaçamento suficiente para evitar poluição.
3. **Clareza de Ação e Feedback:** O resultado da esteira de validação (Aprovado vs. Barrado) deve ser compreensível de forma imediata através de contrastes de cor e sinalizações claras do motivo da recusa.

## 6. Mensagens, validação e recuperação

- **Validação de preenchimento:** exibir a mensagem em português junto ao campo ou arquivo. Ao enviar, levar o foco ao primeiro campo inválido; preservar os demais valores. Informar separadamente nome obrigatório, formato, arquivo vazio, tamanho e quantidade excedidos.
- **Falhas de ações:** usar `ActionErrorDialog` para criação/envio de lote, início/retomada da análise e salvamento de regras. Informar o que aconteceu e o próximo passo. Manter dados locais e chaves de recuperação. Os detalhes técnicos e a referência da API ficam recolhidos em “Detalhes para suporte”.
- **Confirmações:** pedir confirmação antes de descartar a recuperação local de um envio ou substituir a edição de regras pela versão atual. Buscar a configuração antes de substituir os valores locais; uma falha na recarga preserva a edição.
- **Carregamentos e atualização automática:** manter `ErrorNotice` na seção, com uma ação para tentar novamente. Polling não abre modais. Avisos de demonstração, base cadastral, pendências e erros do processamento permanecem consultáveis na página.
- **Sucesso:** mostrar notificação breve ao salvar regras. O envio concluído navega para o acompanhamento. Detalhes de recebíveis continuam em modal aberto pelo usuário.
- **Acessibilidade:** diálogos têm título e descrição associados, navegação por teclado e retorno de foco ao fechar. Em divergência dos arquivos de recuperação, o foco volta à seleção. Os diálogos se ajustam à largura do celular.

## 7. Status e atualização de resultados

- Distinguir envio concluído de análise concluída: após o envio, orientar o usuário a iniciar a análise quando essa ação estiver disponível.
- Usar “Recusado” para decisões das regras e “Dados inválidos” para linhas que não puderam ser analisadas. Ausência de diagnóstico nunca deve sugerir aprovação.
- A primeira consulta de resultados é carregada ao abrir o acompanhamento após o envio. Durante o processamento, a primeira página acompanha a atualização do lote; filtros são preservados.
- Ao navegar para outras páginas, manter o cursor da consulta e oferecer uma ação para carregar os resultados recentes. Quando o arquivo ou lote encerrar o processamento, atualizar automaticamente a consulta a partir da primeira página, com aviso e mantendo os filtros.
- A atualização automática acompanha a pausa do acompanhamento em aba oculta e termina com o processamento. Falhas continuam como avisos na seção, com opção de tentar novamente.
