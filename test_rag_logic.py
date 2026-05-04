from src.rag import RAGManager
from src.config import Config
import os

def test_rag():
    print("--- Testing RAG Retrieval ---")
    rag = RAGManager()
    
    query1 = "vacaciones"
    print(f"Query: {query1} (Category: RRHH)")
    ctx1 = rag.retrieve_context(query1, "RRHH")
    print(f"Context found: {bool(ctx1)}")
    if ctx1:
        print(f"Snippet: {ctx1[:100]}...")
    
    query2 = "vpn for work"
    print(f"\nQuery: {query2} (Category: TECNOLOGIA)")
    ctx2 = rag.retrieve_context(query2, "TECNOLOGIA")
    print(f"Context found: {bool(ctx2)}")
    if ctx2:
        print(f"Snippet: {ctx2[:100]}...")

if __name__ == "__main__":
    # Ensure we are in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    test_rag()
