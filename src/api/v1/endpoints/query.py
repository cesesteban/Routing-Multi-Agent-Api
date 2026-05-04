from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.core.config import Config
from src.core.exceptions import BaseAppException
from src.database.session import get_db
from src.repositories.query_repository import QueryRepository
from src.schemas.query_schemas import DetailedQueryResponse, QueryRequest, QueryResponse
from src.services.routing_service import RoutingService

router = APIRouter()

def get_routing_service(db: AsyncSession = Depends(get_db)):
    repo = QueryRepository(db)
    return RoutingService(repo)

@router.post("/query", response_model=DetailedQueryResponse)
async def process_new_query(request: QueryRequest, service: RoutingService = Depends(get_routing_service)):
    """Inicia el flujo multi-agente para procesar una consulta."""
    return await service.process_query(request.query, lang=request.lang, to_email=request.to_email)

@router.get("/history", response_model=List[QueryResponse])
async def get_query_history(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Obtiene el historial de consultas persistido."""
    repo = QueryRepository(db)
    return await repo.get_all(skip=skip, limit=limit)

@router.get("/query/{query_id}", response_model=DetailedQueryResponse)
async def get_query_detail(query_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene los detalles completos de una consulta específica."""
    repo = QueryRepository(db)
    item = await repo.get_by_id(query_id)
    if not item:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return item
