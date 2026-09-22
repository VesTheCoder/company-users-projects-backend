class AppError(Exception):
    def __init__(
        self, status: int, code: str, detail: str, headers: dict | None = None
    ):
        self.status = status
        self.code = code
        self.detail = detail
        self.headers = headers or {}
        super().__init__(detail)
