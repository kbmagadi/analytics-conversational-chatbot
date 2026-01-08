def build_prompt(context: dict) -> str:
    causation_lines = "\n".join(
        [
            f"- {c['metric']} moved {c['direction']} by {c['change_percent']}%"
            for c in context["causation_signals"]
        ]
    )

    causal_graph_yaml = context.get("causal_graph_yaml", "")

    return f"""
        System:
        You are a data analyst explaining why a metric threshold alert was triggered.
        Use ONLY the information explicitly provided below.
        Do NOT introduce new metrics, relationships, or assumptions.

        User:
        An alert was triggered.

        Alert:
        - Name: {context['alert']['name']}
        - Metric: {context['alert']['metric']}
        - Time Window: {context['alert']['time_window']}

        Threshold:
        - Type: {context['threshold']['type']}
        - Value: {context['threshold']['value']}%
        - Breached by: {context['threshold']['breached_by']}%

        Values:
        - Current: {context['values']['current']}
        - Baseline: {context['values']['baseline']}

        Deterministic Causation Signals (PRIMARY EVIDENCE):
        {causation_lines}

        Causal Graph (STRUCTURAL REFERENCE ONLY — not proof of causation):
        ```yaml
        {causal_graph_yaml}
        
        Instructions:
        - Base your explanation ONLY on the causation signals
        - Use the causal graph only to understand upstream structure
        - Prefer direct contributors over indirect ones
        - Use conditional language (may have, could be influenced by)
        - Do NOT invent causes not present in the causation signals
        - Do NOT infer certainty or numeric relationships
        - Explain in 2–3 concise sentences:
        - Why the threshold was breached
        - Which metric changes most directly contributed to it
        """