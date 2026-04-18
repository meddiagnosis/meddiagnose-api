"""
Build the disease knowledge graph from Wikipedia and AIIMS books.

Merges knowledge_index.json (Wikipedia) and knowledge_index_aiims.json (AIIMS/StatPearls)
into a unified graph with diseases, symptoms, treatments, and causes.

Usage:
    cd backend
    python scripts/build_knowledge_graph.py

    # Build from Wikipedia only (default)
    python scripts/build_knowledge_graph.py

    # Build from both sources (requires AIIMS index)
    python scripts/build_knowledge_graph.py --merge-aiims

Output:
    disease_books/knowledge_graph.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.disease_knowledge_graph import build_graph_from_index

BOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "disease_books"
WIKI_INDEX = BOOKS_DIR / "knowledge_index.json"
AIIMS_INDEX = BOOKS_DIR / "knowledge_index_aiims.json"
AIIMS_SYLLABUS_INDEX = BOOKS_DIR / "knowledge_index_aiims_syllabus.json"
OUTPUT_GRAPH = BOOKS_DIR / "knowledge_graph.json"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build disease knowledge graph")
    parser.add_argument("--merge-aiims", action="store_true", help="Merge AIIMS/StatPearls index if present")
    args = parser.parse_args()

    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    all_nodes = {}
    all_edges = []
    sources = []

    # Wikipedia
    if WIKI_INDEX.exists():
        with open(WIKI_INDEX) as f:
            wiki_index = json.load(f)
        wiki_graph = build_graph_from_index(wiki_index, source="wikipedia")
        for nid, ndata in wiki_graph.get("nodes", {}).items():
            if nid in all_nodes and all_nodes[nid].get("source") != "wikipedia":
                ndata["source"] = "wikipedia,aiims"
            all_nodes[nid] = ndata
        all_edges.extend(wiki_graph.get("edges", []))
        sources.append("wikipedia")
        print(f"  Wikipedia: {len(wiki_index)} diseases -> {len(wiki_graph.get('nodes', {}))} nodes, {len(wiki_graph.get('edges', []))} edges")
    else:
        print(f"  Warning: {WIKI_INDEX} not found. Run download_disease_books.py first.")

    # AIIMS (StatPearls)
    if args.merge_aiims and AIIMS_INDEX.exists():
        with open(AIIMS_INDEX) as f:
            aiims_index = json.load(f)
        aiims_graph = build_graph_from_index(aiims_index, source="aiims")
        for nid, ndata in aiims_graph.get("nodes", {}).items():
            if nid in all_nodes:
                ndata["source"] = all_nodes[nid].get("source", "") + ",aiims"
            all_nodes[nid] = ndata
        # Add edges, avoid duplicates
        seen_edges = {(e["from"], e["to"], e["relation"]) for e in all_edges}
        for e in aiims_graph.get("edges", []):
            key = (e["from"], e["to"], e["relation"])
            if key not in seen_edges:
                all_edges.append(e)
                seen_edges.add(key)
        sources.append("aiims")
        print(f"  AIIMS: {len(aiims_index)} diseases -> merged")
    elif args.merge_aiims and not AIIMS_INDEX.exists():
        print(f"  Warning: {AIIMS_INDEX} not found. Run: python scripts/download_disease_books.py --source aiims -n 80")

    # AIIMS official syllabus (curriculum context)
    if args.merge_aiims and AIIMS_SYLLABUS_INDEX.exists():
        with open(AIIMS_SYLLABUS_INDEX) as f:
            syllabus_index = json.load(f)
        syllabus_graph = build_graph_from_index(syllabus_index, source="aiims_syllabus")
        for nid, ndata in syllabus_graph.get("nodes", {}).items():
            all_nodes[nid] = ndata
        seen_edges = {(e["from"], e["to"], e["relation"]) for e in all_edges}
        for e in syllabus_graph.get("edges", []):
            key = (e["from"], e["to"], e["relation"])
            if key not in seen_edges:
                all_edges.append(e)
                seen_edges.add(key)
        sources.append("aiims_syllabus")
        print(f"  AIIMS syllabus: {len(syllabus_index)} curriculum entries -> merged")

    if not all_nodes:
        print("No data to build graph. Exiting.")
        sys.exit(1)

    graph = {
        "nodes": all_nodes,
        "edges": all_edges,
        "sources": sources,
    }

    with open(OUTPUT_GRAPH, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"\nDone. Graph saved to {OUTPUT_GRAPH}")
    print(f"  Nodes: {len(all_nodes)}")
    print(f"  Edges: {len(all_edges)}")


if __name__ == "__main__":
    main()
