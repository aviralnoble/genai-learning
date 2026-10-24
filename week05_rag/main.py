"""Interactive terminal REPL orchestrating RAG routing, retrieval, and synthesis."""

import sys
from rich.panel import Panel

from src.retrieval.query_router import route_query
from src.retrieval.vector_store import build_retriever
from src.synthesis.generator import generate_curated_answer
from src.utils.console import (
    console,
    display_curated_answer,
    display_retrieval_metrics,
    display_startup_banner,
)


def main() -> None:
    display_startup_banner()

    while True:
        try:
            query = console.input("\n[bold yellow]Query > [/bold yellow]").strip()
            if not query:
                continue
            if query.lower() in {"exit", "quit", "q"}:
                console.print("[dim]Terminating session. Goodbye.[/dim]")
                sys.exit(0)

            with console.status("[bold green]Planning query intent with Claude...[/bold green]"):
                plan = route_query(query)

            with console.status(f"[bold cyan]Executing {plan.search_type.upper()} retrieval in ChromaDB...[/bold cyan]"):
                retriever = build_retriever(
                    search_type=plan.search_type,
                    metadata_filter=plan.metadata_filter if plan.metadata_filter else None,
                )
                retrieved_docs = retriever.invoke(plan.cleaned_query)

            if not retrieved_docs:
                console.print(
                    Panel(
                        "[bold red]No matching documents found in vector store.[/bold red]\n"
                        "Verify that data ingestion has been run (`python ingest.py`) or adjust query filters.",
                        border_style="red",
                    )
                )
                continue

            display_retrieval_metrics(plan, retrieved_docs)

            with console.status("[bold magenta]Curating synthesized response with Claude Sonnet...[/bold magenta]"):
                answer, thinking_status = generate_curated_answer(query, retrieved_docs)

            display_curated_answer(answer, thinking_status)

        except KeyboardInterrupt:
            console.print("\n[dim]Process interrupted. Exiting...[/dim]")
            sys.exit(0)
        except Exception as exc:
            console.print(f"[bold red]Pipeline Error:[/bold red] {exc}", style="red")


if __name__ == "__main__":
    main()