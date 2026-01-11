class ConversationMemory:
    """
    Scoped, deterministic memory for resolving follow-up questions.
    """

    def __init__(self):
        self.last_metric = None
        self.last_period = None
        self.last_compare_to = None
        self.last_intent = None

    def update(self, intent, query_plan):
        if query_plan.get("metric"):
            self.last_metric = query_plan["metric"]

        if query_plan.get("period"):
            self.last_period = query_plan["period"]

        if query_plan.get("compare_to"):
            self.last_compare_to = query_plan["compare_to"]

        self.last_intent = intent

    def resolve(self, intent, query_plan):
        resolved = dict(query_plan)

        # -----------------------------
        # Metric resolution
        # -----------------------------
        if not resolved.get("metric") and self.last_metric:
            resolved["metric"] = self.last_metric

        # -----------------------------
        # Period resolution (INTENT-AWARE)
        # -----------------------------
        if not resolved.get("period") and self.last_period:

            # VALUE intent only supports point-in-time periods
            if intent.name == "VALUE" and self.last_period in {
                "today", "yesterday", "latest"
            }:
                resolved["period"] = self.last_period

            # SUMMARY / TREND can reuse aggregated periods
            elif intent.name in {"SUMMARY", "TREND"}:
                resolved["period"] = self.last_period

        # -----------------------------
        # Comparison resolution
        # -----------------------------
        if (
            intent.name in {"COMPARISON", "ROOT_CAUSE"}
            and not resolved.get("compare_to")
            and self.last_compare_to
        ):
            resolved["compare_to"] = self.last_compare_to

        return resolved

