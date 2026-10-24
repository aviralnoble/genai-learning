# GenAI Learning

Hands-on repository tracking weekly projects transitioning enterprise integration and MFT engineering principles into Generative AI workflows.

---

## Weekly Modules

### Week 1: First LLM API Call

Minimal working Python client interacting with Anthropic's Claude Messages API.

* Implemented baseline client call using the Anthropic Python SDK.
* Configured local environment and secure API key management.

### Week 2: Prompt Engineering & Benchmarking

Structured incident triage extractor evaluated across prompting strategies using Claude Sonnet 5.5.

* Built production extraction pipeline with Pydantic schema validation.
* Evaluated Zero-Shot, XML-delimited, and Few-Shot strategies via Promptfoo.
* Benchmarked deterministic schema compliance, token costs, and prompt injection defense.

### Week 3: Embeddings & Vector Search

Local semantic search pipeline mapping enterprise MFT/B2Bi operational incidents to remediation runbooks.

* Integrated persistent ChromaDB storage with idempotent document ingestion using local ONNX embeddings (`all-MiniLM-L6-v2`).
* Built an interactive CLI evaluating cosine distance metrics for zero-keyword semantic retrieval across protocol failure runbooks.
* Benchmarked atomic document-level chunking against naive token splitting to preserve operational context.

### Week 4: LangChain Core Concepts & LCEL RAG

Rebuilt operational incident search into a streaming RAG pipeline using LangChain core abstractions and LCEL orchestration.

* Migrated manual indexing to standardized `Document` schemas and isolated Chroma collections using `FastEmbed` CPU ONNX embeddings.
* Composed an LCEL pipeline (`prompt | llm | parser`) integrating top-k cosine similarity retrieval with real-time token streaming via `claude-sonnet-5-5`.
* Profiled execution waterfalls, token consumption, and retrieval latency via LangSmith tracing, documenting abstraction overhead versus raw SDKs.

### Week 5: Intent-Routed RAG & Retrieval Deduplication

Modular RAG pipeline over enterprise MFT protocols and EDI standards pairing query-intent routing with dynamic retrieval and semantic deduplication.

* Engineered an upfront intent classifier with Claude Sonnet using Pydantic schemas to dynamically emit retrieval modes (`similarity` vs. `mmr`) and deterministic metadata filters.
* Implemented token-aware chunking (512 tokens, 64-token overlap via `tiktoken`) and tuned Maximal Marginal Relevance ($\lambda = 0.4, k = 2$) to eliminate semantic near-duplicates under constrained candidate pools.
* Developed grounded synthesis middleware enforcing strict source provenance and negative constraints, orchestrated via an interactive Rich CLI REPL.

---

## Requirements

* Python 3.10+
* Anthropic SDK
* Pydantic & pydantic-settings
* Node.js (for Promptfoo evaluation)
* ChromaDB
* LangChain (`langchain`, `langchain-core`, `langchain-chroma`, `langchain-anthropic`, `langchain-huggingface`)
* FastEmbed
* Hugging Face Transformers (`sentence-transformers`)
* tiktoken
* Rich
* PyYAML

---

## Setup

1. Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/aviralnoble/genai-learning.git
cd genai-learning

```