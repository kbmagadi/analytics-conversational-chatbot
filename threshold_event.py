# models/threshold_event.py

class ThresholdEvent:
    def __init__(
        self,
        rule_name,
        metric,
        current_value,
        baseline_value,
        threshold_type,
        threshold_value,
        time_window,
        supporting_metrics=None,
        causal_graph_yaml: str | None = None
    ):
        self.rule_name = rule_name
        self.metric = metric
        self.current_value = current_value
        self.baseline_value = baseline_value
        self.threshold_type = threshold_type
        self.threshold_value = threshold_value
        self.time_window = time_window
        self.supporting_metrics = supporting_metrics or {}

        self.causal_graph_yaml = causal_graph_yaml
