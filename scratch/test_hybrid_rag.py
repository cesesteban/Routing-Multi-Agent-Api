import asyncio
from src.services.ai.rag_service import RAGManager
from src.core.config import Config

async def test_hybrid_search():
    print("--- Testing Hybrid RAG System ---")
    rag = RAGManager()
    
    # Test queries
    queries = [
        {"q": "How do I check my invoices?", "dept": "FINANZAS"},
        {"q": "VPN connection issues", "dept": "TECNOLOGIA"}
    ]
    
    for item in queries:
        print(f"\nQuery: {item['q']} | Department: {item['dept']}")
        try:
            context = rag.retrieve_context(item['q'], item['dept'])
            if context:
                print(f"Result (first 200 chars): {context[:200]}...")
            else:
                print("No context found (Check if you have documents in data/ folder)")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
