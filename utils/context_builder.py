def build_context(event):
    def pct_change(curr, base):
        if base == 0:
            return 0.0
        return round(((curr - base) / base) * 100, 2)

    def extract_numeric(val):
        if isinstance(val, str):
            return float(val.replace("%", ""))
        return float(val)

    # -----------------------------
    # Target metric change
    # -----------------------------
    target_change = pct_change(
        event.current_value,
        event.baseline_value
    )

    causation = []

    # -----------------------------
    # Deterministic causation signals
    # (NO causal graph used here)
    # -----------------------------
    for name, values in event.supporting_metrics.items():
        curr = extract_numeric(values["current"])
        base = extract_numeric(values["baseline"])
        change = pct_change(curr, base)

        # Direction must align with target
        if target_change < 0 and change < 0:
            causation.append({
                "metric": name,
                "direction": "down",
                "change_percent": abs(change)
            })
        elif target_change > 0 and change > 0:
            causation.append({
                "metric": name,
                "direction": "up",
                "change_percent": abs(change)
            })

    # Rank by impact (largest change first)
    causation.sort(
        key=lambda x: x["change_percent"],
        reverse=True
    )

    # -----------------------------
    # Build context for LLM
    # -----------------------------
    context = {
        "alert": {
            "name": event.rule_name,
            "metric": event.metric,
            "time_window": event.time_window
        },
        "threshold": {
            "type": event.threshold_type,
            "value": event.threshold_value,
            "breached_by": abs(target_change)
        },
        "values": {
            "current": event.current_value,
            "baseline": event.baseline_value
        },
        "causation_signals": causation
    }

    # -----------------------------
    # Inject causal graph YAML (verbatim)
    # -----------------------------
    if getattr(event, "causal_graph_yaml", None):
        context["causal_graph_yaml"] = event.causal_graph_yaml

    return context
