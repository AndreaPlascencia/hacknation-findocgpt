import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from models import VectorEmbedding
from app import db

class RAGSystem:
    def __init__(self):
        """Initialize RAG system with OpenAI embeddings"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-ada-002"
        self.chunk_size = 500
        self.overlap = 50
        
    def get_relevant_context(self, query: str, top_k: int = 3) -> str:
        """Get relevant context for a query using RAG"""
        try:
            # Generate embedding for the query
            query_embedding = self._get_embedding(query)
            if query_embedding is None:
                return ""
            
            # Retrieve similar documents from database
            similar_docs = self._find_similar_documents(query_embedding, top_k)
            
            # Combine context from similar documents
            context = self._combine_context(similar_docs)
            
            return context
            
        except Exception as e:
            logging.error(f"Error in get_relevant_context: {str(e)}")
            return ""
    
    def add_document(self, content: str, content_type: str, metadata: Optional[Dict] = None) -> bool:
        """Add a document to the RAG system"""
        try:
            # Split document into chunks
            chunks = self._split_text(content)
            
            for chunk in chunks:
                # Generate embedding
                embedding = self._get_embedding(chunk)
                if embedding is None:
                    continue
                
                # Store in database
                vector_embedding = VectorEmbedding(
                    content=chunk,
                    embedding=json.dumps(embedding.tolist()),
                    content_type=content_type,
                    doc_metadata=json.dumps(metadata) if metadata else None
                )
                
                db.session.add(vector_embedding)
            
            db.session.commit()
            logging.info(f"Added document with {len(chunks)} chunks to RAG system")
            return True
            
        except Exception as e:
            logging.error(f"Error adding document to RAG: {str(e)}")
            db.session.rollback()
            return False
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text.replace("\n", " ")
            )
            return np.array(response.data[0].embedding)
            
        except Exception as e:
            logging.error(f"Error getting embedding: {str(e)}")
            return None
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)
            
            if len(chunk_words) < self.chunk_size:
                break
                
        return chunks
    
    def _find_similar_documents(self, query_embedding: np.ndarray, top_k: int) -> List[Dict]:
        """Find similar documents using cosine similarity"""
        try:
            # Get all embeddings from database
            embeddings_data = VectorEmbedding.query.all()
            
            if not embeddings_data:
                return []
            
            similarities = []
            for embedding_data in embeddings_data:
                try:
                    stored_embedding = np.array(json.loads(embedding_data.embedding))
                    similarity = cosine_similarity(
                        query_embedding.reshape(1, -1),
                        stored_embedding.reshape(1, -1)
                    )[0][0]
                    
                    similarities.append({
                        'content': embedding_data.content,
                        'content_type': embedding_data.content_type,
                        'metadata': json.loads(embedding_data.doc_metadata) if embedding_data.doc_metadata else {},
                        'similarity': similarity
                    })
                    
                except Exception as e:
                    logging.warning(f"Error processing embedding: {str(e)}")
                    continue
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logging.error(f"Error finding similar documents: {str(e)}")
            return []
    
    def _combine_context(self, similar_docs: List[Dict]) -> str:
        """Combine context from similar documents"""
        if not similar_docs:
            return ""
        
        context_parts = []
        for doc in similar_docs:
            context_part = f"[{doc['content_type']}] {doc['content']}"
            if doc['metadata']:
                metadata_str = ", ".join([f"{k}: {v}" for k, v in doc['metadata'].items()])
                context_part += f" ({metadata_str})"
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    def initialize_financial_knowledge(self):
        """Initialize RAG system with basic financial knowledge"""
        try:
            financial_documents = [
                {
                    "content": """Financial KPIs (Key Performance Indicators) are quantifiable measures used to evaluate a company's financial performance. 
                    Common financial KPIs include Revenue (total income), Profit Margin (percentage of revenue that becomes profit), 
                    Earnings Per Share (EPS), Return on Investment (ROI), Debt-to-Equity Ratio, Current Ratio, 
                    Price-to-Earnings Ratio (P/E), Market Capitalization, and Cash Flow.""",
                    "type": "financial_concepts",
                    "metadata": {"topic": "kpis", "category": "fundamentals"}
                },
                {
                    "content": """FinanceBench is a comprehensive dataset containing financial information from public companies. 
                    It includes quarterly and annual financial statements, earnings reports, balance sheets, 
                    cash flow statements, and various financial metrics across different industries and time periods.""",
                    "type": "data_source",
                    "metadata": {"source": "financebench", "category": "dataset"}
                },
                {
                    "content": """Financial forecasting involves predicting future financial performance based on historical data, 
                    market trends, and economic indicators. Common methods include time series analysis, 
                    regression analysis, moving averages, and machine learning models. Forecasts typically cover 
                    revenue projections, expense estimates, cash flow predictions, and profitability analysis.""",
                    "type": "forecasting",
                    "metadata": {"topic": "forecasting", "category": "methodology"}
                }
            ]
            
            for doc in financial_documents:
                self.add_document(doc["content"], doc["type"], doc["metadata"])
                
            logging.info("Initialized RAG system with financial knowledge base")
            
        except Exception as e:
            logging.error(f"Error initializing financial knowledge: {str(e)}")
