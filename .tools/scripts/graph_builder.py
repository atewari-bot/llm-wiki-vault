"""
graph_builder.py — Build a NetworkX DiGraph from Claude-enriched data.
"""
import networkx as nx
import json
from pathlib import Path


def build_graph(enriched: dict) -> nx.DiGraph:
    """
    Build a directed graph from enriched Claude output.
    """
    G = nx.DiGraph()

    # Add entity nodes
    for entity in enriched.get("entities", []):
        G.add_node(
            entity["id"],
            label=entity["label"],
            type=entity.get("type", "concept"),
            aliases=entity.get("aliases", []),
            description=entity.get("description", ""),
            cluster=None,
        )

    # Tag nodes with their cluster
    for cluster in enriched.get("clusters", []):
        for eid in cluster.get("entity_ids", []):
            if G.has_node(eid):
                G.nodes[eid]["cluster"] = cluster["name"]

    # Add relationships as edges
    for rel in enriched.get("relationships", []):
        src, tgt = rel["source"], rel["target"]
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(
                src, tgt,
                type=rel.get("type", "relates_to"),
                confidence=rel.get("confidence", 0.7),
                rationale=rel.get("rationale", ""),
            )

    return G


def graph_to_json(G: nx.DiGraph, enriched: dict) -> dict:
    """Export full graph data as JSON-serializable dict."""
    return {
        "nodes": [
            {
                "id": nid,
                **G.nodes[nid]
            }
            for nid in G.nodes
        ],
        "edges": [
            {
                "source": u,
                "target": v,
                **G.edges[u, v]
            }
            for u, v in G.edges
        ],
        "clusters": enriched.get("clusters", []),
        "gaps": enriched.get("gaps", []),
        "summary": enriched.get("summary", ""),
        "stats": {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "density": round(nx.density(G), 4),
            "connected_components": nx.number_weakly_connected_components(G),
        }
    }


def save_graph_json(graph_data: dict, output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Graph saved → {output_path}")
