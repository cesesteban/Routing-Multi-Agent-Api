from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime

class QueryRequest(BaseModel):
    query: str
    lang: str = "es"

class QueryResponse(BaseModel):
    id: int
    query: str
    intent: Optional[str] = None
    response_text: Optional[str] = None
    priority: Optional[str] = None
    next_steps: Optional[List[str]] = None
    latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    model_used: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class DetailedQueryResponse(QueryResponse):
    confidence: Optional[float] = None
    routing_reason: Optional[str] = None
    audit_trace: Optional[List[dict]] = None
    evaluation_score: Optional[float] = None
    evaluation_justification: Optional[str] = None
    attempts: int = 1
    
    model_config = ConfigDict(from_attributes=True)

class MetricsSummary(BaseModel):
    total_queries: int
    avg_latency_ms: float
    avg_accuracy: float
    total_tokens: int
    total_cost_usd: float
