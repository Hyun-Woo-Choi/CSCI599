"""Tiny local 'corpus' tools for the lecture-06 planning-pattern demos.

Stands in for the "find their docs" step of the worked example (slide 30)
without needing network/web-search access. Deliberately dumb (substring
search over three short local .txt files) - the point is to give the
ReAct executor inside Plan-and-Execute something real to call.
"""
from __future__ import annotations

import pathlib

DOCS_DIR = pathlib.Path(__file__).parent / "docs"

TOOLS = [
    {
        "name": "list_docs",
        "description": "List the available document filenames in the local corpus.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "read_doc",
        "description": "Read the full text of one document by filename.",
        "input_schema": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_docs",
        "description": (
            "Case-insensitive substring search across all documents. "
            "Returns matching lines with filename and line number."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]


def list_docs() -> str:
    return "\n".join(sorted(p.name for p in DOCS_DIR.glob("*.txt")))


def read_doc(filename: str) -> str:
    if "/" in filename or "\\" in filename or ".." in filename:
        return f"error: invalid filename '{filename}'"
    path = DOCS_DIR / filename
    if not path.is_file():
        return f"error: no such document '{filename}'. Call list_docs first."
    return path.read_text()


def search_docs(query: str) -> str:
    hits = []
    for path in sorted(DOCS_DIR.glob("*.txt")):
        for i, line in enumerate(path.read_text().splitlines(), start=1):
            if query.lower() in line.lower():
                hits.append(f"{path.name}:{i}: {line.strip()}")
    return "\n".join(hits) if hits else f"no matches for '{query}'"


def call_tool(name: str, tool_input: dict) -> str:
    if name == "list_docs":
        return list_docs()
    if name == "read_doc":
        return read_doc(tool_input.get("filename", ""))
    if name == "search_docs":
        return search_docs(tool_input.get("query", ""))
    return f"error: unknown tool '{name}'"
