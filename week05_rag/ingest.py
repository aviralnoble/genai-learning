"""CLI entry point to execute the data ingestion pipeline."""

import argparse
import sys
from rich.console import Console
from rich.panel import Panel

from config.settings import settings
from src.ingestion.indexer import run_indexing
from src.retrieval.vector_store import get_vector_store

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest MFT and EDI corpus into ChromaDB.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Wipe and recreate the existing collection before indexing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    console.print(
        Panel.fit(
            f"[bold blue]Corpus Ingestion Pipeline[/bold blue]\n"
            f"Target Directory: [yellow]{settings.data_dir}[/yellow]\n"
            f"Active Chunk Size: [cyan]{settings.chunk_size}[/cyan] tokens (overlap: {settings.chunk_overlap})\n"
            f"Collection: [magenta]{settings.collection_name}[/magenta]",
            title="Ingestion Configuration",
        )
    )

    if args.rebuild:
        console.print("[yellow]Rebuild flag passed. Purging existing Chroma collection...[/yellow]")
        store = get_vector_store()
        try:
            store.delete_collection()
            console.print("[green]Existing collection deleted successfully.[/green]")
        except Exception as exc:
            console.print(f"[dim]Notice on reset: {exc}[/dim]")

    try:
        total_indexed = run_indexing()
        console.print(
            f"[bold green]✔ Ingestion complete.[/bold green] "
            f"Successfully stored [cyan]{total_indexed}[/cyan] chunks in ChromaDB."
        )
    except Exception as exc:
        console.print(f"[bold red]Ingestion failed:[/bold red] {exc}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()