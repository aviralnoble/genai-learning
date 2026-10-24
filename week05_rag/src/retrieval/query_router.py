"""Intent router and dynamic metadata extractor backed by Claude Sonnet."""

import json
from typing import Any, Dict, Literal
import anthropic
from pydantic import BaseModel, Field

from config.settings import settings


class QueryRoutingPlan(BaseModel):
    """Pydantic schema enforcing structured query planning."""

    search_type: Literal["similarity", "mmr"] = Field(
        description="Select 'similarity' for narrow factual lookups; 'mmr' for exploratory, comparative, or troubleshooting queries."
    )
    metadata_filter: Dict[str, Any] = Field(
        default_factory=dict,
        description="Chroma filter dictionary matching metadata tags (e.g. {'domain': 'MFT'}, {'protocol_or_standard': 'AS2'}, {'doc_type': 'troubleshooting'}).",
    )
    cleaned_query: str = Field(
        description="The semantic search query with extraneous conversational phrasing stripped."
    )
    routing_reasoning: str = Field(
        description="Technical justification for chosen search mode and applied metadata filters."
    )


ROUTER_SYSTEM_PROMPT = """You are a specialized query routing engine for an MFT and EDI technical knowledge base.
Analyze incoming user queries and extract a structured JSON routing plan.

Database Metadata Fields Available:
- domain: "MFT" | "EDI"
- protocol_or_standard: "AS2" | "SFTP" | "X12" | "EDIFACT"
- doc_type: "concept" | "troubleshooting"

Routing Decision Rules:
1. 'search_type':
   - Choose 'similarity' if the user asks a pin-point, single-fact question (e.g., ports, envelope tag definitions).
   - Choose 'mmr' if the question is diagnostic, troubleshooting, comparative, or requires diverse context.
2. 'metadata_filter':
   - If the query specifically targets a protocol (e.g. AS2) or standard (e.g. X12), emit a Chroma filter dict.
   - For a single field: {"protocol_or_standard": "AS2"}
   - If no specific metadata restriction is warranted, emit an empty dict {}.
3. 'cleaned_query':
   - Clean the text to optimize dense embedding similarity.

Output MUST be a single raw JSON object adhering to:
{
  "search_type": "similarity" | "mmr",
  "metadata_filter": {},
  "cleaned_query": "string",
  "routing_reasoning": "string"
}
"""


def route_query(user_query: str) -> QueryRoutingPlan:
    """Analyze query with Claude Sonnet, parse thinking blocks, and return validated plan."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.model_id,
        max_tokens=settings.max_tokens,
        thinking={"type": "adaptive"},
        system=ROUTER_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"User Query: {user_query}"}
        ],
    )

    # Parse response content blocks, ignoring thinking blocks to locate text output
    raw_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            raw_text = block.text.strip()
            break

    # Strip code fences if returned by the LLM
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        parsed_json = json.loads(raw_text)
        return QueryRoutingPlan(**parsed_json)
    except Exception as exc:
        # Resilient fallback to MMR without filters if extraction encounters unexpected formatting
        return QueryRoutingPlan(
            search_type="mmr",
            metadata_filter={},
            cleaned_query=user_query,
            routing_reasoning=f"Fallback triggered due to parser error: {exc}",
        )