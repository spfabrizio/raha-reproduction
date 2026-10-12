from pathlib import Path
import networkx as nx
import requests

TOPOLOGY_URL = (
    "https://raw.githubusercontent.com/"
    "mroughan/InternetTopologyZoo/main/"
    "graphml/Cogentco.graphml"
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Cogentco.graphml"


def load_cogentco() -> nx.Graph:
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(TOPOLOGY_URL, timeout=30)
        response.raise_for_status()
        DATA_PATH.write_bytes(response.content)

    graph = nx.read_graphml(DATA_PATH)

    return nx.Graph(graph)


if __name__ == "__main__":
    graph = load_cogentco()
    directed_graph = graph.to_directed()

    print(f"Nodes: {graph.number_of_nodes()}")
    print(f"Undirected edges: {graph.number_of_edges()}")
    print(f"Directed edges: {directed_graph.number_of_edges()}")

    assert graph.number_of_nodes() == 197
    assert graph.number_of_edges() == 243
    assert directed_graph.number_of_edges() == 486

    print("Topology validation passed!")