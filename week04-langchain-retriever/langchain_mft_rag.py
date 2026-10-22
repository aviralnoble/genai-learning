"""
Enterprise MFT Diagnostic Runbook RAG System (LangChain Implementation).

Architecture:
- Ingestion: Validates JSON via Pydantic v2 and maps to LangChain Document schemas.
- Embeddings: Local CPU ONNX execution via FastEmbed (all-MiniLM-L6-v2, 384 dims).
- Vectorstore: LangChain Chroma wrapper targeting an isolated collection with Cosine space.
- Retrieval & Metrics: Extracts top-k candidates, Cosine Distance, and Confidence metrics.
- Synthesis: LCEL chain streaming claude-sonnet-5-5 diagnostic response token-by-token.
"""

import json
import os
import sys
import warnings
from pathlib import Path
from typing import List, Tuple

# Suppress Hugging Face Windows symlink warnings and deprecation noise
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ValidationError


# ==========================================
# 1. Pydantic Runtime Contracts (Exact Week 3 Schema)
# ==========================================

class RunbookRecord(BaseModel):
    """Schema for validating raw MFT operational runbooks matching mft_runbooks.json."""
    id: str = Field(..., description="Unique runbook identifier (e.g., MFT-001)")
    protocol: str = Field(..., description="Protocol context: SFTP, AS2, PGP, etc.")
    title: str = Field(..., description="Runbook title / incident classification")
    content: str = Field(..., description="Observable diagnostic symptoms, cause, and remediation")
    category: str = Field(..., description="Failure category: Authentication, Integrity, Network, etc.")


# ==========================================
# 2. Ingestion & Transformation Logic
# ==========================================

def load_and_transform_runbooks(file_path: Path) -> List[Document]:
    """
    Loads JSON runbooks, validates them via Pydantic, and transforms into LangChain Documents.

    The diagnostic title and detailed content are placed into `page_content` for embedding.
    Operational attributes (id, protocol, category) are stored in `metadata`.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Runbook source file not found at: {file_path.resolve()}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    documents: List[Document] = []
    for item in raw_data:
        try:
            record = RunbookRecord(**item)
        except ValidationError as err:
            print(f"[WARN] Skipping malformed record: {err}", file=sys.stderr)
            continue

        # Searchable diagnostic content for embedding
        page_content = (
            f"Title: {record.title}\n"
            f"Protocol: {record.protocol}\n"
            f"Category: {record.category}\n"
            f"Details: {record.content}"
        )

        # Operational attributes preserved in metadata
        metadata = {
            "runbook_id": record.id,
            "title": record.title,
            "protocol": record.protocol,
            "category": record.category,
        }

        documents.append(Document(page_content=page_content, metadata=metadata))

    return documents


# ==========================================
# 3. Vectorstore Setup & Idempotent Upsert
# ==========================================

def init_vectorstore(
    base_dir: Path,
    collection_name: str = "mft_runbooks_langchain"
) -> Chroma:
    """Initializes Chroma vectorstore with local FastEmbed and ensures idempotent ingestion."""
    persist_dir = str(base_dir / "chroma_db")
    data_file = base_dir / "week03-vector-search" / "data" / "mft_runbooks.json"

    # FastEmbed uses local ONNX all-MiniLM-L6-v2 (384 dimensions)
    embedding_model = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"}
    )

    # Check existing count to ensure idempotency
    existing_count = vectorstore._collection.count()
    if existing_count == 0:
        print(f"[*] Initializing ingestion into collection '{collection_name}'...")
        docs = load_and_transform_runbooks(data_file)
        if not docs:
            raise ValueError(f"No valid runbooks found in {data_file.resolve()}")

        ids = [doc.metadata["runbook_id"] for doc in docs]
        vectorstore.add_documents(documents=docs, ids=ids)
        print(f"[✓] Successfully indexed {len(docs)} runbooks into Chroma.")
    else:
        print(f"[*] Collection '{collection_name}' ready ({existing_count} records indexed).")

    return vectorstore


# ==========================================
# 4. Diagnostic Formatting & Prompt Setup
# ==========================================

RAG_PROMPT_TEMPLATE = """You are a senior enterprise B2Bi/MFT operations engineer.
Analyze the following user operational query and the retrieved incident runbooks.

Context (Retrieved Incident Runbooks):
{context}

Operator Query:
{question}

Provide an actionable, concise operational resolution briefing:
1. Primary Incident Identification (Identify the most probable issue and protocol context).
2. Root Cause Analysis (Explain why this error occurs).
3. Immediate Recovery Checklist (Step-by-step remediation commands/actions based on the runbooks).
4. Preventive Configuration (Recommendations to prevent recurrence).

Maintain a direct, professional engineering tone. Do not use generic filler text."""


def format_context_for_llm(results: List[Tuple[Document, float]]) -> str:
    """Formats retrieved runbooks and metadata into a clean context string for Claude."""
    context_blocks = []
    for rank, (doc, _) in enumerate(results, start=1):
        meta = doc.metadata
        block = (
            f"--- Runbook Match #{rank} ---\n"
            f"ID: {meta.get('runbook_id')}\n"
            f"Title: {meta.get('title')} (Protocol: {meta.get('protocol')})\n"
            f"Category: {meta.get('category')}\n"
            f"Content:\n{doc.page_content}"
        )
        context_blocks.append(block)
    return "\n\n".join(context_blocks)


def print_retrieval_metrics(results: List[Tuple[Document, float]]) -> None:
    """Displays retrieved runbooks with distance and match confidence metrics."""
    print(f"\n{'='*75}")
    print(f"RETRIEVED RUNBOOKS & DISTANCE METRICS (Top {len(results)})")
    print(f"{'='*75}")

    for rank, (doc, raw_distance) in enumerate(results, start=1):
        similarity_pct = max(0.0, (1.0 - (raw_distance / 2.0))) * 100
        meta = doc.metadata

        print(f"[{rank}] [{meta.get('category')}] {meta.get('title')} ({meta.get('protocol')})")
        print(f"    Runbook ID       : {meta.get('runbook_id')}")
        print(f"    Cosine Distance  : {raw_distance:.4f}")
        print(f"    Match Confidence : {similarity_pct:.2f}%")

    print(f"{'='*75}\n")


# ==========================================
# 5. Interactive CLI & Streaming Orchestration
# ==========================================

def run_cli() -> None:
    """Interactive CLI testing retrieval metrics and streaming LCEL synthesis."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[FATAL] ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        print("Set it in your PyCharm Run Configuration or shell environment.", file=sys.stderr)
        sys.exit(1)

    # Determine base directory relative to this script
    script_dir = Path(__file__).resolve().parent
    base_dir = script_dir if (script_dir / "data").exists() else script_dir.parent

    print("Initializing LangChain MFT Operations Assistant...")
    try:
        vectorstore = init_vectorstore(base_dir=base_dir)

        # Initialize Claude Sonnet 5.5
        llm = ChatAnthropic(
            model="claude-sonnet-5-5",
            max_tokens=1500
        )

        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        # LCEL chain for generation
        generation_chain = prompt | llm | StrOutputParser()

    except Exception as e:
        print(f"[FATAL] Setup failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nSystem ready. Enter an operational query or symptom (e.g., 'inode full', 'MDN timeout', 'SFTP host key mismatch').")
    print("Type 'exit' or 'quit' to terminate.\n")

    while True:
        try:
            query = input("mft-ops> ").strip()
            if not query:
                continue
            if query.lower() in {"exit", "quit"}:
                print("Shutting down operations assistant.")
                break

            # 1. Retrieval with Cosine Distance scores
            results = vectorstore.similarity_search_with_score(query, k=3)
            if not results:
                print("\n[!] No matching operational runbooks found.\n")
                continue

            # 2. Print retrieval metrics
            print_retrieval_metrics(results)

            # 3. Stream Claude's synthesized resolution briefing token-by-token
            print("[CLAUDE INCIDENT RESOLUTION BRIEFING]")
            context_str = format_context_for_llm(results)

            stream_gen = generation_chain.stream({
                "context": context_str,
                "question": query
            })

            for chunk in stream_gen:
                sys.stdout.write(chunk)
                sys.stdout.flush()
            print("\n\n" + "-" * 75 + "\n")

        except KeyboardInterrupt:
            print("\nSession interrupted. Exiting.")
            break
        except Exception as e:
            print(f"\n[ERROR] Pipeline execution failed: {e}\n", file=sys.stderr)


if __name__ == "__main__":
    run_cli()