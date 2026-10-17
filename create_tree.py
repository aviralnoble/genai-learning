"""
create_tree.py
Parses ASCII/Unicode directory tree text and generates directories and files on disk.
Compatible with Windows, PyCharm terminal, and console paste.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def parse_tree_line(line: str) -> Tuple[int, str]:
    """
    Extracts indentation depth column and normalized file/folder name from a tree line.
    Handles non-breaking spaces, unicode branch glyphs, and tabs.
    """
    # Normalize tabs and non-breaking spaces
    clean = line.replace("\xa0", " ").replace("\t", "    ").rstrip()

    # Locate the first non-tree glyph character (start of actual filename)
    match = re.search(r"[^\s│\|├└─+\\`-]", clean)
    if not match:
        return 0, ""

    col = match.start()
    name = clean[col:].strip()
    return col, name


def is_directory(name: str, has_children: bool) -> bool:
    """Determines if a node is a directory based on naming and tree hierarchy."""
    if name.endswith("/") or name.endswith("\\"):
        return True
    if has_children:
        return True
    # If no dot extension is present, default to folder
    return "." not in Path(name).name


def build_structure(tree_text: str, root_dir: Path | None = None) -> None:
    """
    Parses multiline tree string and creates corresponding folders and empty files.
    """
    if root_dir is None:
        root_dir = Path.cwd()

    raw_lines = [line for line in tree_text.splitlines() if line.strip()]
    parsed_nodes: List[Tuple[int, str]] = []

    for line in raw_lines:
        col, name = parse_tree_line(line)
        if name:
            parsed_nodes.append((col, name))

    if not parsed_nodes:
        print("[Error] No valid paths found in input.", file=sys.stderr)
        return

    # Stack holds tuples of (column_depth, resolved_path)
    stack: List[Tuple[int, Path]] = [(-1, root_dir)]

    print(f"\n[Scaffolding] Target root: {root_dir.resolve()}\n")

    for i, (col, raw_name) in enumerate(parsed_nodes):
        # Check if the next line in the tree is a child of the current line
        has_children = (i + 1 < len(parsed_nodes)) and (parsed_nodes[i + 1][0] > col)

        # Pop from stack until the top is an ancestor of the current node
        while stack and stack[-1][0] >= col:
            stack.pop()

        parent_path = stack[-1][1]
        clean_name = raw_name.rstrip("/\\")
        target_path = parent_path / clean_name

        if is_directory(raw_name, has_children):
            target_path.mkdir(parents=True, exist_ok=True)
            stack.append((col, target_path))
            print(f"  [DIR]  {target_path.relative_to(root_dir)}/")
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.touch(exist_ok=True)
            print(f"  [FILE] {target_path.relative_to(root_dir)}")

    print("\n[Done] All directories and files created successfully.")


def main() -> None:
    # 1. If a structure file is passed as an argument: python create_tree.py layout.txt
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            tree_text = f.read()
    # 2. If a default 'structure.txt' exists in the current folder
    elif os.path.exists("structure.txt"):
        print("[Info] Reading tree from 'structure.txt'...")
        with open("structure.txt", "r", encoding="utf-8") as f:
            tree_text = f.read()
    # 3. Interactive paste mode directly in PyCharm Run window
    else:
        print("=== Directory Tree Scaffolder ===")
        print("Paste your tree layout below. Press Enter twice on an empty line to build:\n")
        lines = []
        while True:
            try:
                line = input()
                if not line and lines and not lines[-1]:
                    break
                lines.append(line)
            except EOFError:
                break
        tree_text = "\n".join(lines)

    build_structure(tree_text)


if __name__ == "__main__":
    main()