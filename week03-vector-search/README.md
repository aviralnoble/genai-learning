# MFT Operations Semantic Vector Search (ChromaDB)

A local, production-grade vector search engine built to map unstructured B2B/MFT operational incident symptoms directly to standard operating procedure (SOP) remediation runbooks.

## Architecture

- **Vector Engine**: ChromaDB persistent client (`./chroma_db`)
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions, running locally via ONNX)
- **Distance Metric**: Cosine Distance ($1.0 - \text{Cosine Similarity}$)
- **Validation**: Pydantic v2 schemas for runtime contract enforcement on ingestion and search outputs
- **Corpus**: 12 structured enterprise operational failure scenarios across SFTP, AS2, PGP, and staging file systems

## Quickstart

1. **Initialize Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt