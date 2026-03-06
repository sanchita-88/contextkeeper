import networkx as nx
from typing import List, Dict, Any

# In-memory directed graph — nodes are functions, edges are call relationships
_graph = nx.DiGraph()


def add_file(filepath: str, parsed: dict):
    """Add all functions and their relationships from a parsed file to the graph."""
    functions = parsed.get("functions", [])
    imports = parsed.get("imports", [])

    for func in functions:
        node_id = f"{filepath}::{func['full_name']}"
        _graph.add_node(
            node_id,
            file=filepath,
            name=func["name"],
            full_name=func["full_name"],
            start_line=func["start_line"],
            end_line=func["end_line"],
        )

    # Add edges based on import cross-references (simple heuristic)
    for func in functions:
        func_node = f"{filepath}::{func['full_name']}"
        for imp in imports:
            # Find other nodes that match names in this import
            for node in _graph.nodes:
                node_data = _graph.nodes[node]
                name = node_data.get("name", "")
                if name and name in imp and node != func_node:
                    _graph.add_edge(func_node, node)


def get_context_for_query(query: str) -> str:
    """Return a text description of graph relationships relevant to the query."""
    if _graph.number_of_nodes() == 0:
        return "No graph data available."

    # Find nodes whose name is mentioned in the query
    query_lower = query.lower()
    relevant_nodes = [
        n for n in _graph.nodes
        if _graph.nodes[n].get("name", "").lower() in query_lower
    ]

    if not relevant_nodes:
        # Sample a small part of the graph
        sample = list(_graph.nodes)[:5]
        return f"Graph has {_graph.number_of_nodes()} functions. Sample: {', '.join(sample[:5])}"

    lines = []
    for node in relevant_nodes[:3]:
        successors = list(_graph.successors(node))[:5]
        predecessors = list(_graph.predecessors(node))[:5]
        lines.append(f"{node} calls: {successors}")
        lines.append(f"{node} called by: {predecessors}")

    return "\n".join(lines)


def get_impact(function_name: str) -> Dict[str, Any]:
    """BFS from a function node to find all downstream callers (what breaks)."""
    # Find the node matching the function name
    matching = [
        n for n in _graph.nodes
        if _graph.nodes[n].get("name") == function_name
        or _graph.nodes[n].get("full_name") == function_name
    ]

    if not matching:
        return {
            "functions": [],
            "files": [],
            "risk_level": "unknown",
            "explanation": f"Function '{function_name}' not found in the code graph.",
        }

    start_node = matching[0]
    # BFS over predecessors (callers)
    affected_nodes = set()
    queue = list(_graph.predecessors(start_node))
    visited = {start_node}

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        affected_nodes.add(node)
        queue.extend(_graph.predecessors(node))

    affected_functions = [_graph.nodes[n].get("full_name", n) for n in affected_nodes]
    affected_files = list(set(_graph.nodes[n].get("file", "") for n in affected_nodes))

    risk = "low"
    if len(affected_nodes) > 10:
        risk = "high"
    elif len(affected_nodes) > 4:
        risk = "medium"

    return {
        "functions": affected_functions[:20],
        "files": affected_files[:10],
        "risk_level": risk,
        "explanation": (
            f"Changing '{function_name}' directly affects {len(affected_nodes)} callers "
            f"across {len(affected_files)} files."
        ),
    }


def clear():
    """Reset the graph (useful for re-indexing)."""
    _graph.clear()
