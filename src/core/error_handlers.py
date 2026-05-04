from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.core.exceptions import BaseAppException, ProviderException
import logging

logger = logging.getLogger("uvicorn.error")

async def app_exception_handler(request: Request, exc: BaseAppException):
    """Handler for controlled application exceptions."""
    is_unavailable = isinstance(exc, ProviderException)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "unavailable" if is_unavailable else "error",
            "code": exc.__class__.__name__,
            "message": exc.message,
            "detail": exc.detail
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """Handler for uncontrolled/unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Detectar errores de conexión comunes de proveedores externos
    exc_name = exc.__class__.__name__
    is_connection_error = any(
        err in exc_name 
        for err in ["APIConnectionError", "ConnectError", "ServiceUnavailable", "Timeout"]
    )
    
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE if is_connection_error else status.HTTP_500_INTERNAL_SERVER_ERROR
    status_str = "unavailable" if is_connection_error else "error"
    error_code = "ProviderUnavailable" if is_connection_error else "InternalServerError"
    message = (
        "El servicio de IA no se encuentra disponible momentáneamente."
        if is_connection_error 
        else "Ha ocurrido un error inesperado. Por favor, contacte al soporte."
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_str,
            "code": error_code,
            "message": message,
            "detail": str(exc) if (request.app.debug or is_connection_error) else None
        }
    )
