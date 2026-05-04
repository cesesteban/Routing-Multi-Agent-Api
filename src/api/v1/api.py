from fastapi import APIRouter
from src.api.v1.endpoints.query import router as query_router
from src.api.v1.endpoints.resources import router as resources_router

api_router = APIRouter()
api_router.include_router(query_router, tags=["Agents"])
api_router.include_router(resources_router, tags=["Resources"])
