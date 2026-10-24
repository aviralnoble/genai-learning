"""Synthesis middleware curating answers using Claude Sonnet with Adaptive Thinking."""

from typing import List, Tuple
import anthropic
from langchain_core.documents import Document

from config.settings import settings

SYNTHESIS_SYSTEM_PROMPT = """You are an expert enterprise integration architect specializing in B2B integration (B2Bi), EDI standards (ANSI X12, UN/EDIFACT), and Managed File Transfer (MFT) protocols (AS2, SFTP).

Guidelines:
1. Ground your answer strictly on the provided Context excerpts.
2. If the context does not contain sufficient information to answer authoritatively, state clearly what is known and identify the missing data.
3. Explicitly cite source documents and relevant metadata (e.g., protocol, standard) when stating architectural facts or troubleshooting remediations.
4. Maintain technical, concise, and non-buzzword enterprise terminology (e.g., non-repudiation, MIC, envelope hierarchies, atomic rename).
"""


def generate_curated_answer(
    user_query: str, retrieved_docs: List[Document]
) -> Tuple[str, str]:
    """Generate synthesized answer from retrieved chunks using Claude Sonnet.

    Args:
        user_query: Original user question.
        retrieved_docs: Chunks fetched by vector retrieval.

    Returns:
        Tuple of (final_curated_text, thinking_summary_or_status).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Build context payload with document provenance
    context_blocks = []
    for idx, doc in enumerate(retrieved_docs, start=1):
        source = doc.metadata.get("source", "unknown")
        proto = doc.metadata.get("protocol_or_standard", "general")
        doc_type = doc.metadata.get("doc_type", "reference")
        header = f"--- [Document {idx}: {source} | Protocol: {proto} | Type: {doc_type}] ---"
        context_blocks.append(f"{header}\n{doc.page_content}")

    formatted_context = "\n\n".join(context_blocks)

    user_message_content = f"""Context Excerpts:
{formatted_context}

Question:
{user_query}
"""

    response = client.messages.create(
        model=settings.model_id,
        max_tokens=settings.max_tokens,
        thinking={"type": "adaptive"},
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message_content}
        ],
    )

    final_text = ""
    thinking_summary = "Adaptive thinking completed."

    # Parse response content blocks for TextBlock and ThinkingBlock
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            final_text = block.text
        elif block_type == "thinking":
            thinking_summary = getattr(block, "thinking", "Active reasoning block generated.")

    return final_text, thinking_summary