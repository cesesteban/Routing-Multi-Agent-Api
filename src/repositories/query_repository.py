from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database.models import QueryRecord
from typing import List, Optional

class QueryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> QueryRecord:
        db_item = QueryRecord(**data)
        self.db.add(db_item)
        await self.db.commit()
        await self.db.refresh(db_item)
        return db_item

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[QueryRecord]:
        result = await self.db.execute(select(QueryRecord).offset(skip).limit(limit).order_by(QueryRecord.created_at.desc()))
        return result.scalars().all()

    async def get_by_id(self, query_id: int) -> Optional[QueryRecord]:
        result = await self.db.execute(select(QueryRecord).where(QueryRecord.id == query_id))
        return result.scalar_one_or_none()
