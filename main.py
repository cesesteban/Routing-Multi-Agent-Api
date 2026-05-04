import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database.session import engine, Base
import os

from src.api.v1.api import api_router
from src.core.config import Config
from src.core.error_handlers import app_exception_handler, global_exception_handler
from src.core.exceptions import BaseAppException

app = FastAPI(
    title="Multi-Agent Routing System API",
    description="Sistema experto de orquestación de agentes con RAG y Auditoría",
    version="1.0.0"
)

# Exception Handlers
app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    # Crear tablas si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Base de datos inicializada...")

@app.get("/")
async def root():
    return {
        "message": "Multi-Agent Routing System API is online",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
