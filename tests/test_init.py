from agents import MultiAgentSystem
from config import Config

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
