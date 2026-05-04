import asyncio
import json
from src.schemas.query_schemas import QueryRequest
from src.services.routing_service import RoutingService
from src.repositories.query_repository import QueryRepository
from src.database.session import engine, Base, SessionLocal

async def test_languages():
    # Inicializar DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    db = SessionLocal()
    repo = QueryRepository(db)
    service = RoutingService(repo)
    
    test_queries = [
        {"query": "¿Cómo puedo ver mis facturas?", "lang": "es"},
        {"query": "How can I see my invoices?", "lang": "en"}
    ]
    
    for tq in test_queries:
        print(f"\n--- Testing Language: {tq['lang']} ---")
        try:
            result = await service.process_query(tq["query"], lang=tq["lang"])
            print(f"Query: {tq['query']}")
            print(f"Intent: {result.intent}")
            print(f"Response: {result.response_text[:100]}...")
        except Exception as e:
            print(f"Error: {e}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(test_languages())
