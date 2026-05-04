from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from datetime import datetime
from .session import Base

class QueryRecord(Base):
    __tablename__ = "query_records"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    
    # Routing Data
    intent = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    routing_reason = Column(Text, nullable=True)
    
    # Specialist Response
    response_text = Column(Text, nullable=True)
    priority = Column(String, nullable=True)
    next_steps = Column(JSON, nullable=True) # List of strings
    
    # Audit & Eval
    audit_trace = Column(JSON, nullable=True) # List of dicts
    evaluation_score = Column(Float, nullable=True)
    evaluation_justification = Column(Text, nullable=True)
    
    # Metrics
    latency_ms = Column(Float, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    
    # System Metadata
    model_used = Column(String, nullable=True)
    attempts = Column(Integer, default=1)
    context_hash = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
