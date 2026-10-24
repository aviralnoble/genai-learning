"""Corpus ingestion and token-aware chunking pipeline."""

from pathlib import Path
from typing import Any, Dict, List
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings
from src.retrieval.vector_store import get_vector_store


def infer_metadata(file_path: Path) -> Dict[str, Any]:
    """Derive deterministic metadata tags based on file naming patterns."""
    stem = file_path.stem.lower()
    meta: Dict[str, Any] = {
        "source": file_path.name,
        "domain": "UNKNOWN",
        "protocol_or_standard": "UNKNOWN",
        "doc_type": "concept",
    }

    if "as2" in stem:
        meta["domain"] = "MFT"
        meta["protocol_or_standard"] = "AS2"
    elif "sftp" in stem:
        meta["domain"] = "MFT"
        meta["protocol_or_standard"] = "SFTP"
    elif "x12" in stem:
        meta["domain"] = "EDI"
        meta["protocol_or_standard"] = "X12"
    elif "edifact" in stem:
        meta["domain"] = "EDI"
        meta["protocol_or_standard"] = "EDIFACT"

    if "troubleshooting" in stem:
        meta["doc_type"] = "troubleshooting"

    return meta


def run_indexing() -> int:
    """Load, split, and persist markdown files into the local Chroma collection.

    Returns:
        Total number of chunks persisted.
    """
    data_path = Path(settings.data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory '{data_path}' does not exist.")

    raw_docs: List[Document] = []
    for file_path in data_path.glob("*.md"):
        loader = TextLoader(str(file_path), encoding="utf-8")
        loaded = loader.load()
        metadata = infer_metadata(file_path)
        for doc in loaded:
            doc.metadata.update(metadata)
        raw_docs.extend(loaded)

    if not raw_docs:
        raise ValueError(f"No .md documents found in '{data_path}' to index.")

    # Split using token-based windowing (configurable: 256 / 512 / 1024 tokens)
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-4o",  # Standard cl100k_base tokenizer for accurate token lengths
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(raw_docs)

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    return len(chunks)