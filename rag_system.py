import os
import re
import json
import glob
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from models import VectorEmbedding
# Import the shared database instance
from app import db

def _guess_company_from_filename(name: str) -> Optional[str]:
    m = re.match(r"([A-Z]{1,6})[_\-].*", name)
    return m.group(1) if m else None


class RAGSystem:
    def __init__(self):
        logging.info("[RAG] Inicializando sistema RAG")
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        self.chunk_size = 500  # en palabras
        self.overlap = 50

    # ====== Embeddings y almacenamiento ======

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Genera embeddings usando OpenAI"""
        try:
            resp = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text.replace("\n", " ")
            )
            return np.array(resp.data[0].embedding)
        except Exception as e:
            logging.error(f"[RAG] Error creando embedding: {e}")
            return None

    #====== Almacenamiento en BD ======
    def _save_embedding(self, text: str, embedding: np.ndarray, metadata: Dict[str, Any], content_type: str = "document"):
        """Guarda chunk + embedding en la BD"""
        vector_embedding = VectorEmbedding(
            content=text,
            embedding=json.dumps(embedding.tolist()),
            content_type=content_type,
            doc_metadata=json.dumps(metadata) if metadata else None
        )
        db.session.add(vector_embedding)

    # ====== Chunking ======

    def _chunk_text(self, text: str, max_chars: int = 4000, overlap: int = 300) -> List[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
            if start < 0:
                start = 0
        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Chunk por palabras (para textos cortos tipo notas)"""
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)
            if len(chunk_words) < self.chunk_size:
                break
        return chunks

    # ====== Ingesta de PDFs ======

    def ingest_pdf_file(self, filepath: str):
        if not os.path.isfile(filepath):
            return
        reader = PdfReader(filepath)
        doc_name = os.path.basename(filepath)
        company = _guess_company_from_filename(doc_name)

        for page_idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            chunks = self._chunk_text(text, max_chars=4000, overlap=300)
            for i, ch in enumerate(chunks, start=1):
                metadata = {
                    "doc_name": doc_name,
                    "company": company,
                    "page_num": page_idx,
                    "chunk": i,
                    "source_path": os.path.abspath(filepath),
                }
                emb = self._get_embedding(ch)
                if emb is not None:
                    self._save_embedding(ch, emb, metadata, content_type="pdf_page")

    def ingest_pdfs_from_dir(self, dirpath: str, pattern: str = "*.pdf", limit: Optional[int] = None):
        files = sorted(glob.glob(os.path.join(dirpath, pattern)))
        if limit:
            files = files[:limit]
        for f in files:
            try:
                self.ingest_pdf_file(f)
            except Exception as e:
                logging.error(f"[RAG] Falló PDF {f}: {e}")
        db.session.commit()

    # ====== Ingesta de evidencias JSONL ======

    def ingest_jsonl_evidence_file(self, jsonl_path: str):
        if not os.path.isfile(jsonl_path):
            return
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                evidence = (
                    rec.get("evidence_text_full_page")
                    or rec.get("evidence_text")
                    or ""
                ).strip()
                if not evidence:
                    continue
                meta = {
                    "doc_name": rec.get("document_name") or rec.get("doc_name"),
                    "company": rec.get("company_symbol") or rec.get("company"),
                    "page_num": rec.get("page_num") or rec.get("page"),
                    "source_path": rec.get("document_local_path"),
                    "source_url": rec.get("document_url"),
                    "q_id": rec.get("id") or rec.get("question_id"),
                }
                chunks = self._chunk_text(evidence, max_chars=4000, overlap=300)
                for i, ch in enumerate(chunks, start=1):
                    meta_i = dict(meta)
                    meta_i["chunk"] = i
                    emb = self._get_embedding(ch)
                    if emb is not None:
                        self._save_embedding(ch, emb, meta_i, content_type="jsonl_evidence")
        db.session.commit()

    # ====== Carga completa de FinanceBench local ======

    def ingest_all_local_financebench(self, pdf_dir: str = "./data/pdfs", jsonl_dir: str = "./data/jsonl"):
        """Carga todos los PDFs y JSONL de las rutas dadas"""
        logging.info(f"[RAG] Iniciando ingesta de PDFs desde {pdf_dir}")
        self.ingest_pdfs_from_dir(pdf_dir)
        logging.info(f"[RAG] Iniciando ingesta de evidencias JSONL desde {jsonl_dir}")
        jsonl_files = glob.glob(os.path.join(jsonl_dir, "*.jsonl"))
        for jf in jsonl_files:
            self.ingest_jsonl_evidence_file(jf)

    # ====== Recuperación de contexto ======

    def get_relevant_context(self, query: str, top_k: int = 3) -> str:
        # Initialize financial knowledge if not already done
        try:
            if VectorEmbedding.query.count() == 0:
                self.initialize_financial_knowledge()
        except Exception as e:
            logging.error(f"[RAG] Error initializing knowledge: {str(e)}")
        
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return ""
        similar_docs = self._find_similar_documents(query_embedding, top_k)
        return self._combine_context(similar_docs)

    def _find_similar_documents(self, query_embedding: np.ndarray, top_k: int) -> List[Dict]:
        embeddings_data = VectorEmbedding.query.all()
        if not embeddings_data:
            return []
        similarities = []
        for ed in embeddings_data:
            try:
                stored_embedding = np.array(json.loads(ed.embedding))
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    stored_embedding.reshape(1, -1)
                )[0][0]
                similarities.append({
                    'content': ed.content,
                    'content_type': ed.content_type,
                    'metadata': json.loads(ed.doc_metadata) if ed.doc_metadata else {},
                    'similarity': similarity
                })
            except Exception:
                continue
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]

    def _combine_context(self, similar_docs: List[Dict]) -> str:
        context_parts = []
        for doc in similar_docs:
            context_part = f"[{doc['content_type']}] {doc['content']}"
            if doc['metadata']:
                metadata_str = ", ".join(f"{k}: {v}" for k, v in doc['metadata'].items())
                context_part += f" ({metadata_str})"
            context_parts.append(context_part)
        return "\n\n".join(context_parts)
    
    def initialize_financial_knowledge(self):
        """Initialize the RAG system with basic financial knowledge"""
        try:
            # Check if we already have embeddings
            existing_count = VectorEmbedding.query.count()
            if existing_count > 0:
                logging.info(f"[RAG] Already initialized with {existing_count} embeddings")
                return
            
            logging.info("[RAG] Initializing with financial knowledge base")
            
            # Add fundamental financial knowledge
            financial_knowledge = [
                {
                    "content": "Apple Inc. (AAPL) is a technology company that designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories. Key financial metrics include iPhone revenue (typically 50-60% of total revenue), Services revenue (growing segment including App Store, iCloud, Apple Music), and gross margins typically around 37-42%. Apple reports quarterly earnings showing revenue, net income, earnings per share (EPS), and guidance.",
                    "metadata": {"company": "AAPL", "category": "overview", "sector": "technology"}
                },
                {
                    "content": "Microsoft Corporation (MSFT) revenue streams include Productivity and Business Processes (Office 365, Microsoft Teams, LinkedIn), Intelligent Cloud (Azure, Windows Server, SQL Server), and More Personal Computing (Windows, Xbox, Surface). Azure cloud revenue has been growing 40-50% year-over-year. Operating margins are typically 35-42%.",
                    "metadata": {"company": "MSFT", "category": "overview", "sector": "technology"}
                },
                {
                    "content": "Amazon.com Inc. (AMZN) operates in multiple segments: North America retail, International retail, and Amazon Web Services (AWS). AWS is the most profitable segment with operating margins around 30%, while retail has lower margins around 1-5%. Key metrics include net sales, operating income, free cash flow, and Prime membership growth.",
                    "metadata": {"company": "AMZN", "category": "overview", "sector": "e-commerce"}
                },
                {
                    "content": "Alphabet Inc. (GOOGL) revenue primarily comes from Google Search advertising, YouTube advertising, Google Cloud, and Other Bets (including Waymo). Search advertising typically represents 50-60% of total revenue. Operating margins are usually 20-25%. Key metrics include revenue per search, traffic acquisition costs (TAC), and cloud revenue growth.",
                    "metadata": {"company": "GOOGL", "category": "overview", "sector": "technology"}
                },
                {
                    "content": "Tesla Inc. (TSLA) revenue comes from Automotive sales (Model S, 3, X, Y), Energy generation and storage (solar panels, Powerwall), and Services. Automotive gross margins are typically 18-25%. Key metrics include vehicle deliveries, production numbers, average selling price, and energy deployment.",
                    "metadata": {"company": "TSLA", "category": "overview", "sector": "automotive"}
                },
                {
                    "content": "3M Company (MMM) operates in four business segments: Safety and Industrial, Transportation and Electronics, Health Care, and Consumer. Key financial metrics include organic growth rates, operating margins (typically 18-22%), free cash flow conversion, and return on invested capital (ROIC). 3M is known for consistent dividend payments and R&D spending around 6% of sales.",
                    "metadata": {"company": "MMM", "category": "overview", "sector": "industrial"}
                },
                {
                    "content": "Key Performance Indicators (KPIs) in financial analysis include: Revenue (total sales), Gross Profit Margin (gross profit/revenue), Operating Margin (operating income/revenue), Net Profit Margin (net income/revenue), Earnings Per Share (EPS), Price-to-Earnings Ratio (P/E), Return on Equity (ROE), Return on Assets (ROA), Debt-to-Equity Ratio, Current Ratio, and Free Cash Flow.",
                    "metadata": {"category": "kpis", "topic": "financial_metrics"}
                },
                {
                    "content": "Financial statement analysis involves three main statements: Income Statement (shows revenue, expenses, and profit over a period), Balance Sheet (shows assets, liabilities, and equity at a point in time), and Cash Flow Statement (shows cash inflows and outflows from operating, investing, and financing activities). Key ratios include liquidity ratios, profitability ratios, and leverage ratios.",
                    "metadata": {"category": "analysis", "topic": "financial_statements"}
                },
                {
                    "content": "Quarterly earnings reports typically include: Revenue (year-over-year and quarter-over-quarter growth), Earnings Per Share (EPS), Operating margin, Net income, Cash flow from operations, and Forward guidance. Companies also discuss segment performance, market conditions, and strategic initiatives during earnings calls.",
                    "metadata": {"category": "earnings", "topic": "quarterly_reports"}
                },
                {
                    "content": "Common financial forecasting methods include: Time series analysis (using historical trends), Regression analysis (correlating with economic indicators), Scenario analysis (best/worst/expected case), Monte Carlo simulation (probabilistic modeling), and Discounted Cash Flow (DCF) models for valuation.",
                    "metadata": {"category": "forecasting", "topic": "methods"}
                }
            ]
            
            # Process and store each piece of knowledge
            for knowledge in financial_knowledge:
                embedding = self._get_embedding(knowledge["content"])
                if embedding is not None:
                    self._save_embedding(
                        text=knowledge["content"],
                        embedding=embedding,
                        metadata=knowledge["metadata"],
                        content_type="financial_knowledge"
                    )
            
            db.session.commit()
            logging.info(f"[RAG] Initialized with {len(financial_knowledge)} financial knowledge entries")
            
        except Exception as e:
            logging.error(f"[RAG] Error initializing financial knowledge: {str(e)}")
            db.session.rollback()