"""
Tests para verificar que los archivos de prompts son sintácticamente válidos
y pueden ser formateados con todas las variables requeridas sin errores.
"""
import os
import pytest
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List


class RouterResponse(BaseModel):
    intent: str
    confidence: float
    reason: str


class SpecialistResponse(BaseModel):
    response_text: str
    next_steps: List[str]
    priority: str
    requires_supervisor: bool


def _load_prompt(filename: str) -> str:
    """Carga un prompt relativo al directorio del proyecto."""
    prompts_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", filename
    )
    with open(prompts_path, "r", encoding="utf-8") as f:
        return f.read()


def test_router_prompt():
    """El prompt del router debe formatearse correctamente con todas sus variables."""
    template_text = _load_prompt("router_prompt.md")
    prompt = ChatPromptTemplate.from_template(template_text)
    parser = PydanticOutputParser(pydantic_object=RouterResponse)

    # Build input with all variables the template may reference
    input_vars = {k: "test" for k in prompt.input_variables}
    input_vars.update({
        "query": "Test query",
        "language": "es",
        "format_instructions": parser.get_format_instructions(),
    })
    formatted = prompt.invoke(input_vars)
    assert formatted is not None


def test_specialist_prompt():
    """El prompt del especialista debe formatearse correctamente con todas sus variables."""
    template_text = _load_prompt("specialist_prompt.md")
    prompt = ChatPromptTemplate.from_template(template_text)
    parser = PydanticOutputParser(pydantic_object=SpecialistResponse)

    # Build input with all variables the template may reference
    input_vars = {k: "test" for k in prompt.input_variables}
    input_vars.update({
        "role_description": "Test role",
        "tone": "Test tone",
        "query": "Test query",
        "intent": "TECNOLOGIA",
        "reason": "Test reason",
        "language": "es",
        "context": "",
        "feedback": "",
        "format_instructions": parser.get_format_instructions(),
    })
    formatted = prompt.invoke(input_vars)
    assert formatted is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
