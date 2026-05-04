from typing import Optional

class BaseAppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = 500, detail: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)

class ProviderException(BaseAppException):
    """Exception raised when an LLM or Embedding provider is unavailable or fails."""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=503,
            detail=detail
        )

class ServiceException(BaseAppException):
    """Exception raised for business logic failures."""
    def __init__(self, message: str, status_code: int = 400, detail: Optional[str] = None):
        super().__init__(message, status_code, detail)

class ValidationException(BaseAppException):
    """Exception raised for input validation failures."""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=422,
            detail=detail
        )
