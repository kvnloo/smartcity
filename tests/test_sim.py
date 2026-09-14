from smartcity.config import SimConfig
from smartcity.model import load_city
from smartcity.sim import CitySim, demo_metrics


def test_naperville_graph_is_connected_enough():
    city = load_city()
    assert city.graph.number_of_nodes() > 40
    assert city.graph.number_of_edges() > 80
    giant = max(len(c) for c in __import__("networkx").weakly_connected_components(city.graph))
    assert giant / city.graph.number_of_nodes() > 0.4


def test_batch_sim_completes_trips():
    snap = demo_metrics(seconds=12.0, policy="batch", seed=3)
    assert snap["metrics"]["spawned"] > 10
    assert snap["graph"]["nodes"] > 10
    assert snap["metrics"]["active"] + snap["metrics"]["completed"] == snap["metrics"]["spawned"]
