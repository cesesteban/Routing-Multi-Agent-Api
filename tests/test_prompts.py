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

def test_router_prompt():
    print("Testing router_prompt.md...")
    with open("prompts/router_prompt.md", "r", encoding="utf-8") as f:
        template_text = f.read()
    prompt = ChatPromptTemplate.from_template(template_text)
    parser = PydanticOutputParser(pydantic_object=RouterResponse)
    
    # This should not raise KeyError
    formatted = prompt.invoke({
        "query": "Test query",
        "format_instructions": parser.get_format_instructions()
    })
    print("Router prompt formatted successfully.")
    # print(formatted.to_string())

def test_specialist_prompt():
    print("\nTesting specialist_prompt.md...")
    with open("prompts/specialist_prompt.md", "r", encoding="utf-8") as f:
        template_text = f.read()
    prompt = ChatPromptTemplate.from_template(template_text)
    parser = PydanticOutputParser(pydantic_object=SpecialistResponse)
    
    # This should not raise KeyError
    formatted = prompt.invoke({
        "role_description": "Test role",
        "tone": "Test tone",
        "query": "Test query",
        "intent": "Test intent",
        "reason": "Test reason",
        "format_instructions": parser.get_format_instructions()
    })
    print("Specialist prompt formatted successfully.")
    # print(formatted.to_string())

if __name__ == "__main__":
    try:
        test_router_prompt()
        test_specialist_prompt()
    except Exception as e:
        print(f"Error: {e}")
