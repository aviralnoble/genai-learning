# Enterprise MFT & EDI RAG Intelligence Pipeline

A modular, production-grade Retrieval-Augmented Generation (RAG) system built over Managed File Transfer (MFT) protocols (AS2, SFTP) and Electronic Data Interchange (EDI) standards (ANSI ASC X12, UN/EDIFACT).

The pipeline combines dynamic query-intent classification, deterministic metadata filtering, Maximal Marginal Relevance (MMR) deduplication, and an LLM curation middleware powered by Claude Sonnet with Adaptive Thinking.

---

## Architecture Overview

```
User Query
    │
    ▼
[Intent Router (Claude Sonnet 3.5)] ──► Extracts Structured Pydantic Plan:
    │                                     ├── Mode: 'similarity' (narrow facts) vs 'mmr' (diagnostic/broad)
    │                                     ├── Filters: e.g., {'protocol_or_standard': 'AS2', 'domain': 'MFT'}
    │                                     └── Cleaned Semantic Query
    ▼
[Local ChromaDB Vector Store] ─────────► Embeddings: all-MiniLM-L6-v2 (100% Local CPU, 384-dim)
    │
    ▼ (Retrieved Chunks)
[Synthesis Middleware (Claude)] ──────► Enforces source provenance, thinking trace, non-repudiation accuracy
    │
    ▼
Rich Terminal Interface (CLI)

```

---

## Chunking Evaluation & Tradeoff Analysis

The corpus was evaluated across three distinct token-window configurations (tokenized via `tiktoken` with `cl100k_base` encoding) with a constant 64-token sliding window overlap.

| Chunk Size | Framing & Boundary Fidelity | Semantic Density | Retrieval Precision | Failure Mode & Tradeoff Observed |
| --- | --- | --- | --- | --- |
| **256 Tokens** | Splits composite definitions | High (single facts) | Very High | **Context Fragmentation:** An extracted chunk for AS2 MDN captures the receipt verification requirement but loses the parent explanation of the Message Integrity Check (MIC) calculation. |
| **512 Tokens (Selected Baseline)** | Preserves envelope hierarchies | Balanced | Optimal | **Optimal Balance:** Captures complete three-tiered EDI envelope structures (`ISA`/`GS`/`ST`) or enterprise SFTP atomic file transfer sequences (`.filepart` staging + atomic rename) without context clipping. |
| **1024 Tokens** | Retains full multi-page flows | Low (diluted) | Lower | **Semantic Dilution:** Dense vector embeddings average too many unrelated concepts. Specific queries targeting niche parameters (such as `GS02` sender codes or specific S/MIME cipher suites) score lower in cosine similarity. |

---

## Architectural Comparison: Raw ChromaDB SDK vs. LangChain

| Dimension | Raw ChromaDB SDK (`chromadb.PersistentClient`) | LangChain Abstraction (`langchain_chroma.Chroma`) |
| --- | --- | --- |
| **Embedding Engine** | Native integration with internal ONNX runtime (`ONNXMiniLM_L6_V2`); no extra packages. | Uses unified `Embeddings` base class (`langchain_huggingface`); runs locally on CPU without egress. |
| **Retrieval Strategies** | Requires manual mathematical implementation for MMR, diversity reranking, and dynamic thresholding. | First-class native support via `vector_store.as_retriever(search_type="mmr", search_kwargs={"lambda_mult": 0.7})`. |
| **Query Routing & Filters** | Manual translation of natural language queries into Chroma's `$and`, `$or`, `$eq` dict operators. | Seamless translation from Pydantic structured output directly into vector store search arguments. |
| **Observability** | Requires custom OpenTelemetry spans or manual LangSmith run tree injections. | Automatic tracing across document loading, chunking, retrieval, and chain execution via LangSmith. |
| **Production Decision** | Ideal for ultra-low latency, resource-constrained microservices with static retrieval needs. | Ideal for complex agentic pipelines with multi-stage reasoning, adaptive routing, and centralized tracing. |

---

## Project Structure

```text
.
├── config/
│   ├── __init__.py
│   └── settings.py              # Pydantic BaseSettings loading config.yaml & .env
├── config.yaml                  # Configurable chunk size, overlap, k, and MMR lambda
├── data/                        # Technical reference documents & diagnostic mirrors
│   ├── as2_protocol_guide.md
│   ├── as2_troubleshooting.md
│   ├── as2_troubleshooting_duplicate.md  # Semantic mirror for MMR testing
│   ├── edi_x12_standards.md
│   ├── edifact_structure_guide.md
│   └── sftp_mft_enterprise.md
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── indexer.py           # Markdown loader, token-aware splitter, metadata tagger
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── query_router.py      # LLM self-querying & search type classifier
│   │   └── vector_store.py      # Persistent ChromaDB client & retriever factory
│   └── synthesis/
│   │   ├── __init__.py
│   │   └── generator.py         # Claude Sonnet synthesis with Adaptive Thinking
│   └── utils/
│       ├── __init__.py
│       └── console.py         
├── .gitignore
├── ingest.py                    # Standalone corpus ingestion and index rebuild CLI
├── main.py                      # Interactive terminal REPL
├── requirements.txt
└── README.md

```

---

## Installation & Setup

### 1. Prerequisites & Environment

Ensure Python 3.10+ is installed in your local virtual environment:

```bash
# Clone repository and enter directory
git clone [https://github.com/aviralnoble/genai-learning.git]
cd week5-mft-edi-rag

# Activate virtual environment (.venv)
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 2. Configure Secrets

Create a `.env` file in the root directory:

```env
ANTHROPIC_API_KEY="your-anthropic-api-key"
LANGSMITH_API_KEY="your-langsmith-api-key"
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_PROJECT="week5-mft-edi-rag"

```

---

## Usage

### Ingest the Corpus

Process the markdown knowledge base, apply metadata tags, and generate local embeddings in `./chroma_db`:

```bash
python ingest.py

```

To test different chunk sizes (e.g., 256 or 1024 tokens), modify `chunk_size` in `config.yaml` and run with the rebuild flag to purge existing vectors:

```bash
python ingest.py --rebuild

```

### Run the Interactive Terminal

Start the query interface:

```bash
python main.py

```

---

## Validation & Test Scenarios

Test these three distinct query patterns in the interactive terminal to verify intent routing, metadata filtering, and MMR deduplication:

### Scenario 1: Factual Pin-Point Lookup

* **Input:** `"What default TCP port does enterprise SFTP run over?"`
* **Router Decision:** `search_type: "similarity"` | `filter: {"protocol_or_standard": "SFTP"}`
* **Expected Result:** Directly retrieves SFTP specifications without diversity dilution; outputs port 22 and SSH-2 transport details.

### Scenario 2: Diagnostic Query & Deduplication (MMR Stress Test)

* **Input:** `"How do I troubleshoot 'Unable to decrypt S/MIME payload' in AS2?"`
* **Router Decision:** `search_type: "mmr"` | `filter: {"protocol_or_standard": "AS2"}`
* **Expected Result:** Vector store contains two near-identical troubleshooting chunks (`as2_troubleshooting.md` and `as2_troubleshooting_duplicate.md`). MMR penalizes the redundant chunk and pulls distinct context on certificate management and MIC calculation.

### Scenario 3: Cross-Domain Structural Comparison

* **Input:** `"Compare the envelope structures between ANSI ASC X12 and UN/EDIFACT."`
* **Router Decision:** `search_type: "mmr"` | `filter: {"domain": "EDI"}`
* **Expected Result:** Filters out all MFT (AS2/SFTP) context and retrieves X12 envelopes (`ISA`/`GS`/`ST`) alongside EDIFACT syntax envelopes (`UNA`/`UNB`/`UNH`) for synthesis.