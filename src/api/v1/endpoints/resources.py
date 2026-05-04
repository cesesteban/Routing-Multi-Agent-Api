from fastapi import APIRouter, Depends
from typing import List
from src.services.resource_service import ResourceService
from src.schemas.resource_schemas import PromptResponse, KnowledgeCategoryResponse

router = APIRouter()

def get_resource_service():
    """Factory para obtener la instancia del servicio de recursos."""
    return ResourceService()

@router.get("/prompts", response_model=List[PromptResponse])
def get_prompts(service: ResourceService = Depends(get_resource_service)):
    """
    Lista todos los prompts disponibles y su contenido.
    """
    return service.get_all_prompts()

@router.get("/knowledge", response_model=List[KnowledgeCategoryResponse])
def get_knowledge_base(service: ResourceService = Depends(get_resource_service)):
    """
    Lista las categorías y archivos de la base de conocimiento.
    """
    return service.get_knowledge_base()
