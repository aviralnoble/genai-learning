## Architectural Comparison: Raw ChromaDB vs. LangChain RAG Abstraction

In Week 4, the MFT Diagnostic Search was rebuilt using LangChain core abstractions and extended with an LCEL retrieval-augmented generation (RAG) pipeline powered by `claude-sonnet-5-5`.

### Implementation Comparison

| Architectural Dimension | Week 3: Raw ChromaDB SDK | Week 4: LangChain Core Abstraction |
| :--- | :--- | :--- |
| **Dependency Footprint** | Minimal (`chromadb`, `pydantic`). Direct SQLite/HNSW interface. | Higher (`langchain`, `langchain-chroma`, `langchain-anthropic`, `fastembed`). |
| **Document Schema** | Raw Python dicts; separate arrays for `ids`, `metadatas`, and `documents`. | Standardized `Document(page_content, metadata)` object model. |
| **Embeddings** | Internal default ONNX runtime (`all-MiniLM-L6-v2`). | Explicit embedding object (`FastEmbedEmbeddings`) decoupled from DB client. |
| **Execution Flow** | Procedural calls (`collection.query(...)`) with manual string parsing. | Declarative LCEL pipeline (`prompt \| llm \| parser`) implementing the `Runnable` protocol. |
| **Output Delivery** | Static CLI printout of nearest matching runbooks. | Top-3 metric reporting + real-time token-by-token streaming via `chain.stream()`. |
| **Storage Isolation** | Default collection in `./chroma_db`. | Isolated `mft_runbooks_langchain` collection in `./chroma_db`. |

### Key Engineering Takeaways

1. **Tradeoffs of the Retriever Abstraction**:
   Calling `vectorstore.as_retriever().invoke()` provides a clean, unified interface for downstream LLM prompts, but abstracts away distance and similarity scores. For operational diagnostics where confidence thresholds dictate remediation paths, direct scoring via `similarity_search_with_score()` is necessary before formatting context for LLM synthesis.

2. **Preventing Semantic Bleeding**:
   Operational runbooks share procedural troubleshooting language (e.g., `check permissions`, `restart listener`, `inspect firewall`). Consolidating diagnostic symptoms and error codes in `page_content` while storing step-by-step remediation in `metadata` prevents semantic dilution and false-positive cross-protocol matches.

3. **LCEL Composition vs. Ad-Hoc Scripts**:
   LangChain’s `Runnable` protocol provides consistent interfaces (`invoke`, `stream`, `batch`). Combining retrieval with `ChatAnthropic` in an LCEL pipeline enables native streaming and clean context injection with minimal glue code.