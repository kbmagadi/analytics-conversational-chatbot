import yaml
from pathlib import Path


class CausalGraph:
    def __init__(self, path="causal_graph.yaml"):
        self.path = Path(path)
        self.graph = self._load()

    def _load(self):
        with open(self.path) as f:
            return yaml.safe_load(f)["metrics"]

    # -----------------------------
    # Read-only helpers
    # -----------------------------

    def metrics(self):
        return list(self.graph.keys())

    def causes_of(self, metric):
        return self.graph.get(metric, {}).get("causes", [])

    def has_metric(self, metric):
        return metric in self.graph
