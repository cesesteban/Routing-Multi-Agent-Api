import os
from typing import List
from src.core.config import Config
from src.schemas.resource_schemas import PromptResponse, KnowledgeCategoryResponse

class ResourceService:
    """Servicio para gestionar los recursos del sistema (prompts y base de conocimiento)."""

    def get_all_prompts(self) -> List[PromptResponse]:
        """
        Lista todos los prompts disponibles en el directorio configurado.
        """
        if not os.path.exists(Config.PROMPTS_DIR):
            return []
        
        prompts = []
        for file in os.listdir(Config.PROMPTS_DIR):
            if file.endswith(".md"):
                file_path = os.path.join(Config.PROMPTS_DIR, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        prompts.append(PromptResponse(
                            name=file.replace("_prompt.md", "").capitalize(),
                            filename=file,
                            content=content
                        ))
                except Exception as e:
                    # Log error if needed, for now skip corrupted files
                    continue
        return prompts

    def get_knowledge_base(self) -> List[KnowledgeCategoryResponse]:
        """
        Lista las categorías y archivos de la base de conocimiento en la carpeta 'data'.
        """
        if not os.path.exists(Config.BASE_DATA_DIR):
            return []
        
        categories = []
        for item in os.listdir(Config.BASE_DATA_DIR):
            item_path = os.path.join(Config.BASE_DATA_DIR, item)
            if os.path.isdir(item_path):
                try:
                    files = [f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))]
                    categories.append(KnowledgeCategoryResponse(
                        category=item,
                        files=files,
                        total_files=len(files)
                    ))
                except Exception:
                    continue
        return categories
