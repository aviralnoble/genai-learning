"""
MFT Operations Diagnostic Vector Search System.

Embeds and indexes enterprise MFT/B2Bi operational runbooks using ChromaDB's
local embedding engine (all-MiniLM-L6-v2) and provides an interactive semantic
retrieval CLI interface.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.api.models.Collection import Collection
from pydantic import BaseModel, Field, ValidationError

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mft_vector_search")

# -----------------------------------------------------------------------------
# Configuration Constants
# -----------------------------------------------------------------------------
DATA_FILE_PATH = Path("data/mft_runbooks.json")
CHROMA_PERSIST_DIR = Path("./chroma_data")
COLLECTION_NAME = "mft_runbooks"
TOP_K_RESULTS = 3


# -----------------------------------------------------------------------------
# Domain Schemas (Pydantic Runtime Validation)
# -----------------------------------------------------------------------------
class RunbookRecord(BaseModel):
    """Schema validating an individual runbook entry from disk."""

    id: str = Field(..., description="Unique runbook identifier (e.g., MFT-001)")
    protocol: str = Field(..., description="Transport or protocol layer (e.g., AS2, SFTP)")
    title: str = Field(..., description="Human-readable issue title")
    content: str = Field(..., description="Diagnostic details and remediation steps")
    category: str = Field(..., description="Classification category")


class SearchResult(BaseModel):
    """Schema representing a standardized retrieval output."""

    id: str
    protocol: str
    title: str
    content: str
    category: str
    distance: float


# -----------------------------------------------------------------------------
# Ingestion & Database Management
# -----------------------------------------------------------------------------
def load_runbooks_from_file(file_path: Path) -> List[RunbookRecord]:
    """
    Read and validate runbook records from a JSON file.

    Args:
        file_path: Path to the JSON data file.

    Returns:
        List of validated RunbookRecord objects.

    Raises:
        FileNotFoundError: If the source JSON file does not exist.
        ValueError: If JSON parsing or Pydantic validation fails.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Data file not found at: {file_path.resolve()}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if not isinstance(raw_data, list):
            raise ValueError(f"Expected a top-level JSON array in {file_path}")

        records = [RunbookRecord.model_validate(item) for item in raw_data]
        logger.info("Successfully validated %d runbook records from %s", len(records), file_path)
        return records

    except (json.JSONDecodeError, ValidationError) as e:
        logger.error("Failed to parse or validate data file: %s", str(e))
        raise ValueError(f"Corrupt or invalid runbook schema: {e}") from e


def initialize_vector_store(
    persist_dir: Path,
    collection_name: str,
    records: List[RunbookRecord],
) -> Collection:
    """
    Initialize persistent ChromaDB client and index records idempotently.

    Uses default all-MiniLM-L6-v2 ONNX embeddings and cosine distance metric.

    Args:
        persist_dir: Directory where ChromaDB indexes are persisted.
        collection_name: Name of the target vector collection.
        records: List of validated records to ingest.

    Returns:
        chromadb.Collection instance ready for querying.
    """
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    # Configure collection with cosine distance (hnsw:space = cosine)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_count = collection.count()
    target_count = len(records)

    # Idempotent upsert: skip indexing if documents are already present
    if existing_count >= target_count:
        logger.info(
            "Collection '%s' already indexed with %d documents. Skipping ingestion.",
            collection_name,
            existing_count,
        )
        return collection

    logger.info("Indexing %d runbook entries into collection '%s'...", target_count, collection_name)

    ids = [record.id for record in records]
    documents = [f"{record.title}. {record.content}" for record in records]
    metadatas: List[Dict[str, Any]] = [
        {
            "protocol": record.protocol,
            "title": record.title,
            "category": record.category,
        }
        for record in records
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info("Vector indexing complete. Total stored chunks: %d", collection.count())
    return collection


# -----------------------------------------------------------------------------
# Query Service
# -----------------------------------------------------------------------------
def query_runbooks(
    collection: Collection,
    query_text: str,
    top_k: int = TOP_K_RESULTS,
) -> List[SearchResult]:
    """
    Execute semantic similarity query against the vector store.

    Args:
        collection: The ChromaDB collection to query.
        query_text: Natural language query string.
        top_k: Number of nearest neighbors to retrieve.

    Returns:
        List of structured SearchResult objects sorted by relevance.
    """
    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    search_results: List[SearchResult] = []

    # Parse and validate nested ChromaDB result arrays
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for item_id, doc, meta, dist in zip(ids, docs, metas, distances):
        search_results.append(
            SearchResult(
                id=item_id,
                protocol=str(meta.get("protocol", "UNKNOWN")),
                title=str(meta.get("title", "Untitled")),
                content=doc,
                category=str(meta.get("category", "General")),
                distance=round(float(dist), 4),
            )
        )

    return search_results


# -----------------------------------------------------------------------------
# Console Presentation & Interactive CLI
# -----------------------------------------------------------------------------
def display_results(query: str, results: List[SearchResult]) -> None:
    """Format and display search results to the terminal."""
    print("\n" + "=" * 80)
    print(f"QUERY: \"{query}\"")
    print(f"RETRIEVED: Top {len(results)} matches (Distance metric: Cosine [0.0 = exact, 1.0 = unrelated])")
    print("=" * 80)

    if not results:
        print("[-] No matching runbooks found.")
        return

    for rank, res in enumerate(results, start=1):
        # Convert cosine distance to an approximate semantic similarity percentage
        similarity_pct = max(0.0, round((1.0 - res.distance) * 100, 1))

        print(f"\n[Rank #{rank}] {res.title}")
        print(f"  Identifier  : {res.id}")
        print(f"  Protocol    : {res.protocol} | Category: {res.category}")
        print(f"  Relevance   : Cosine Distance = {res.distance:.4f} (~{similarity_pct}% similarity)")
        print(f"  SOP Detail  : {res.content}")
        print("-" * 80)


def start_interactive_cli(collection: Collection) -> None:
    """Run interactive query-response loop in console."""
    print("\n" + "=" * 80)
    print("  MFT & EDI Operations Diagnostic Search (ChromaDB Local Vector Engine)")
    print("  Type any operational symptom or error, or 'exit' / 'quit' to terminate.")
    print("=" * 80 + "\n")

    while True:
        try:
            user_input = input("mft-search > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", ":q"):
                print("\nExiting search console. Goodbye.")
                break

            results = query_runbooks(collection, user_input, top_k=TOP_K_RESULTS)
            display_results(user_input, results)

        except KeyboardInterrupt:
            print("\n\nProcess interrupted by user. Exiting.")
            break
        except Exception as e:
            logger.error("An error occurred during search: %s", str(e), exc_info=True)


# -----------------------------------------------------------------------------
# Application Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Bootstrap application data, storage, and CLI."""
    try:
        runbook_records = load_runbooks_from_file(DATA_FILE_PATH)
        collection = initialize_vector_store(
            persist_dir=CHROMA_PERSIST_DIR,
            collection_name=COLLECTION_NAME,
            records=runbook_records,
        )
        start_interactive_cli(collection)
    except Exception as e:
        logger.critical("Fatal initialization failure: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()