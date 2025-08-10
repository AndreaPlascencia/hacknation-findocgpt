import os
from app import app, socketio
import logging
from rag_system import RAGSystem

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    rag = RAGSystem()

    if os.getenv("RAG_BOOTSRAP", "0") == "1":
        data_dir = os.getenv("FINANCEBENCH_DATA_DIR", ".")
        pdf_dir = os.path.join(data_dir, "pdfs")
        jsonl_path = os.path.join(data_dir, "data", "financebench_open_source.jsonl")

    # 1) PDFs
    try:
        rag.ingest_pdfs_from_dir(pdf_dir)
    except Exception as e:
        logging.error(f"Error ingesting PDFs: {str(e)}")

    try:
        rag.ingest_jsonl_evidence_file(jsonl_path) 
    except Exception as e:
        logging.error(f"Error ingesting JSONL evidence: {str(e)}")
 
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
        
