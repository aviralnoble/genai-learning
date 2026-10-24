"""Vector store initialization and retriever factory module."""

from pathlib import Path
from typing import Any, Dict, Optional
import chromadb
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import settings


def get_embedding_function() -> HuggingFaceEmbeddings:
    """Instantiate local CPU sentence-transformers embedding model."""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vector_store() -> Chroma:
    """Initialize persistent Chroma vector store with persistent storage client."""
    db_path = Path(settings.chroma_db_dir)
    db_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(db_path))
    embeddings = get_embedding_function()

    return Chroma(
        client=client,
        collection_name=settings.collection_name,
        embedding_function=embeddings,
    )


def build_retriever(
    search_type: str = "similarity",
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> VectorStoreRetriever:
    """Build a configured VectorStoreRetriever supporting MMR and metadata filtering.

    Args:
        search_type: Either 'similarity' or 'mmr'.
        metadata_filter: Optional dict of Chroma metadata filter expressions.

    Returns:
        Configured VectorStoreRetriever instance.
    """
    vector_store = get_vector_store()
    search_kwargs: Dict[str, Any] = {"k": settings.k_retrieval}

    if metadata_filter:
        search_kwargs["filter"] = metadata_filter

    if search_type == "mmr":
        # fetch_k defines candidate pool from which diverse k items are picked
        search_kwargs.update(
            {
                "fetch_k": max(settings.k_retrieval * 3, 10),
                "lambda_mult": settings.mmr_lambda,
            }
        )
        return vector_store.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs,
        )

    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )