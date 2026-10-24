class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 422,
        retry: bool = False,
        details: list | None = None,
        current_version: str | None = None,
    ):
        super().__init__(message)
        self.code, self.status, self.retry = code, status, retry
        self.details, self.current_version = details or [], current_version

    def dto(self) -> dict:
        return {
            "codigo": self.code,
            "mensagem": str(self),
            "retry_permitido": self.retry,
            "detalhes": self.details,
            "versao_atual": self.current_version,
        }
