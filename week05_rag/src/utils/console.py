"""Console visualization and formatting utilities using Rich."""

from typing import List
from langchain_core.documents import Document
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import settings

console = Console()


def display_startup_banner() -> None:
    """Render startup dashboard displaying active system configuration."""
    details = (
        f"[bold cyan]Model:[/bold cyan] {settings.model_id} (Adaptive Thinking)\n"
        f"[bold cyan]Chunk Size:[/bold cyan] {settings.chunk_size} tokens (overlap: {settings.chunk_overlap})\n"
        f"[bold cyan]Default Top-K:[/bold cyan] {settings.k_retrieval} | [bold cyan]MMR Lambda:[/bold cyan] {settings.mmr_lambda}\n"
        f"[bold cyan]Database:[/bold cyan] {settings.chroma_db_dir} ({settings.collection_name})\n"
        f"[bold cyan]LangSmith Tracing:[/bold cyan] {settings.langchain_tracing_v2} (Project: {settings.langchain_project})"
    )
    console.print(
        Panel(
            details,
            title="[bold green]MFT & EDI RAG Intelligence Terminal[/bold green]",
            subtitle="Type 'exit' or 'quit' to terminate session",
            border_style="green",
        )
    )


def display_retrieval_metrics(plan, docs: List[Document]) -> None:
    """Render structured tables summarizing intent routing and retrieved chunks.

    Args:
        plan: Validated QueryRoutingPlan instance from query_router.
        docs: List of Document objects returned by the retriever.
    """
    routing_table = Table(title="Query Intent Routing Plan", show_header=True, header_style="bold magenta")
    routing_table.add_column("Property", style="dim", width=20)
    routing_table.add_column("Resolved Value")

    routing_table.add_row("Search Type", plan.search_type.upper())
    routing_table.add_row(
        "Metadata Filters",
        str(plan.metadata_filter) if plan.metadata_filter else "None (Global Search)",
    )
    routing_table.add_row("Cleaned Query", plan.cleaned_query)
    routing_table.add_row("Routing Reasoning", plan.routing_reasoning)
    console.print(routing_table)

    chunks_table = Table(title="Retrieved Chunks from Vector Store", show_header=True, header_style="bold blue")
    chunks_table.add_column("#", width=3)
    chunks_table.add_column("Source Document", style="cyan")
    chunks_table.add_column("Protocol / Std", style="yellow")
    chunks_table.add_column("Doc Type", style="green")
    chunks_table.add_column("Excerpt Preview", style="white")

    for idx, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "N/A")
        proto = doc.metadata.get("protocol_or_standard", "N/A")
        dtype = doc.metadata.get("doc_type", "N/A")
        preview = doc.page_content.replace("\n", " ")[:90] + "..."
        chunks_table.add_row(str(idx), source, proto, dtype, preview)

    console.print(chunks_table)


def display_curated_answer(answer: str, thinking_status: str) -> None:
    """Render synthesized response panel with thinking trace summary.

    Args:
        answer: Final text output from Claude.
        thinking_status: Summary or content of the reasoning/thinking block.
    """
    console.print(
        Panel(
            f"[dim italic]Thinking trace: {thinking_status[:160]}...[/dim italic]\n\n{answer}",
            title="[bold green]Curated Architecture Synthesis[/bold green]",
            border_style="green",
        )
    )