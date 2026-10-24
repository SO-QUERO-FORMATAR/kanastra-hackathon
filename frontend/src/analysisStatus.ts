import type { DTO } from "./api/client";
import { label } from "./utils";

const labels: Record<string, string> = {
  RECEBENDO: "Recebendo arquivos",
  ENVIO_CONCLUIDO: "Envio concluído",
  AGUARDANDO_UPLOAD: "Aguardando envio",
  RECEBIDO: "Arquivo recebido",
  NA_FILA: "Análise na fila",
  INDEXANDO: "Preparando dados",
  PRONTO: "Pronto para análise",
  BLOQUEADO: "Aguardando correção de pendências",
  ANALISANDO: "Análise em andamento",
  CONCLUIDO: "Análise concluída",
  CONCLUIDO_COM_ERROS: "Concluído com erros",
  FALHOU: "Processamento interrompido",
  APROVADO: "Aprovado",
  BARRADO: "Recusado",
  ERRO_DADOS: "Dados inválidos",
  AGUARDANDO: "Aguardando início",
  INDEXACAO: "Preparação dos dados",
  ANALISE: "Análise dos recebíveis",
  FINALIZADO: "Processamento encerrado",
};
export const statusLabel = (status: string) => labels[status] ?? label(status);
export const isTerminal = (status?: string) =>
  ["CONCLUIDO", "CONCLUIDO_COM_ERROS", "FALHOU"].includes(status ?? "");
export function statusTone(status: string) {
  if (["CONCLUIDO", "APROVADO", "RECEBIDO", "ENVIO_CONCLUIDO"].includes(status))
    return "positive";
  if (["FALHOU", "BARRADO", "ERRO_DADOS"].includes(status)) return "negative";
  return "pending";
}
export function lotMessage(lot: DTO<"LoteDTO">) {
  switch (lot.status) {
    case "RECEBENDO":
      return lot.acoes.pode_iniciar
        ? "Envio concluído. Clique em Iniciar análise para processar os recebíveis."
        : "O envio ainda não terminou. Retome o envio dos arquivos para continuar.";
    case "NA_FILA":
      return "Envio concluído. A análise está na fila e começará automaticamente.";
    case "INDEXANDO":
      return "Estamos preparando os dados dos arquivos. Os resultados serão atualizados automaticamente.";
    case "ANALISANDO":
      return "Análise em andamento. Os resultados parciais são atualizados automaticamente.";
    case "BLOQUEADO":
      return lot.acoes.pode_retomar
        ? "A análise aguarda a correção das pendências abaixo. Depois, clique em Retomar análise."
        : "A análise está bloqueada. Consulte as pendências e as ações disponíveis abaixo para continuar.";
    case "CONCLUIDO":
      return "Análise concluída. Consulte os recebíveis aprovados e recusados na tabela.";
    case "CONCLUIDO_COM_ERROS":
      return "Processamento concluído com erros em linhas ou arquivos. Consulte os diagnósticos dos itens afetados.";
    case "FALHOU":
      return "O processamento foi interrompido. Consulte o motivo abaixo e a ação disponível para continuar. Os resultados existentes podem estar incompletos.";
  }
}
export function resultMessage(result: DTO<"ResultadoDTO">) {
  if (result.tipo === "ERRO_DADOS" || !result.status)
    return (
      result.erros_dados[0]?.mensagem ??
      "Não foi possível analisar esta linha. Revise os dados de origem."
    );
  if (result.status === "BARRADO")
    return (
      result.motivos[0]?.mensagem ??
      "Recebível recusado pelas regras do fundo. Consulte os detalhes."
    );
  return "Recebível aprovado pelas regras do fundo.";
}
export const refusalLabels: Record<DTO<"CodigoRecusa">, string> = {
  NOTA_DUPLICADA: "Nota duplicada",
  CNPJ_SACADO_VALIDO: "CNPJ do sacado inválido",
  SITUACAO_CADASTRAL_SACADO: "Situação cadastral não permitida",
  TIPO_RECEBIVEL: "Tipo de recebível não permitido",
  VALOR_MINIMO: "Valor abaixo do mínimo",
  NAO_VENCIDA: "Recebível vencido",
  PRAZO_MINIMO: "Prazo abaixo do mínimo",
  PRAZO_MAXIMO: "Prazo acima do máximo",
  CONCENTRACAO_MAXIMA_SACADO: "Limite de concentração por sacado excedido",
  CONCENTRACAO_MAXIMA_CEDENTE: "Limite de concentração por cedente excedido",
};
