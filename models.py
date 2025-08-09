from app import db
from datetime import datetime
from sqlalchemy import Text, DateTime, Float, Integer, String

class ChatSession(db.Model):
    """Model to store chat sessions"""
    id = db.Column(Integer, primary_key=True)
    session_id = db.Column(String(255), unique=True, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatMessage(db.Model):
    """Model to store individual chat messages"""
    id = db.Column(Integer, primary_key=True)
    session_id = db.Column(String(255), nullable=False)
    message = db.Column(Text, nullable=False)
    response = db.Column(Text)
    message_type = db.Column(String(50), nullable=False)  # 'user' or 'bot'
    kpis_extracted = db.Column(Text)  # JSON string of extracted KPIs
    timestamp = db.Column(DateTime, default=datetime.utcnow)

class FinancialData(db.Model):
    """Model to cache financial data from FinanceBench"""
    id = db.Column(Integer, primary_key=True)
    company_symbol = db.Column(String(10), nullable=False)
    metric_name = db.Column(String(100), nullable=False)
    metric_value = db.Column(Float)
    period = db.Column(String(50))
    year = db.Column(Integer)
    quarter = db.Column(Integer)
    data_source = db.Column(String(100))
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VectorEmbedding(db.Model):
    """Model to store vector embeddings for RAG system"""
    id = db.Column(Integer, primary_key=True)
    content = db.Column(Text, nullable=False)
    embedding = db.Column(Text, nullable=False)  # JSON string of vector
    content_type = db.Column(String(50), nullable=False)  # 'financial_report', 'kpi', etc.
    doc_metadata = db.Column(Text)  # JSON string of additional metadata
    created_at = db.Column(DateTime, default=datetime.utcnow)
