from pydantic import BaseModel
from typing import List

class PromptResponse(BaseModel):
    """Schema para la respuesta de un prompt individual."""
    name: str
    filename: str
    content: str

class KnowledgeCategoryResponse(BaseModel):
    """Schema para la respuesta de una categoría de la base de conocimiento."""
    category: str
    files: List[str]
    total_files: int
