import sys
import os
import pytest

# Añadir src al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.services.ai.agent_service import MultiAgentSystem
from src.core.config import Config

def test_initialization():
    print(f"Testing initialization with PROVIDER={Config.LLM_PROVIDER}...")
    try:
        system = MultiAgentSystem()
        print("MultiAgentSystem initialized successfully.")
        print(f"LLM type: {type(system.llm)}")
    except Exception as e:
        print(f"Initialization failed: {e}")

if __name__ == "__main__":
    test_initialization()
