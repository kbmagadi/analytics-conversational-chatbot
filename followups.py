from intent_classifier import Intent

# -----------------------------
# Capability constraints
# -----------------------------

SUPPORTED_TREND_PERIOD = "last_7_days"


def suggest_followups(intent, query_plan, response_context=None):
    """
    Return a small set of safe, executable follow-up questions.
    Follow-ups must NEVER suggest unsupported operations.
    """

    suggestions = []

    metric = query_plan.get("metric")
    period = query_plan.get("period")

    # -----------------------------
    # SUMMARY → drill-down options
    # -----------------------------
    if intent == Intent.SUMMARY:
        suggestions.append("Why did revenue change?")
        suggestions.append("Show traffic trend over the last 7 days")

    # -----------------------------
    # ROOT CAUSE (daily) → explore drivers / context
    # -----------------------------
    elif intent == Intent.ROOT_CAUSE:
        if metric:
            suggestions.append(
                f"Show {metric.lower()} trend over the last 7 days"
            )
        suggestions.append("Give me a summary for today")

    # -----------------------------
    # PERIOD ROOT CAUSE (weekly) → safe expansions
    # -----------------------------
    elif intent == Intent.PERIOD_ROOT_CAUSE:
        suggestions.append("Show traffic trend over the last 7 days")
        suggestions.append("Why did conversion rate change yesterday?")

    # -----------------------------
    # VALUE → comparison or trend
    # -----------------------------
    elif intent == Intent.VALUE:
        if metric:
            suggestions.append(
                f"Compare {metric.lower()} today vs yesterday"
            )
            suggestions.append(
                f"Show {metric.lower()} trend over the last 7 days"
            )

    # -----------------------------
    # COMPARISON → explanation or trend
    # -----------------------------
    elif intent == Intent.COMPARISON:
        if metric:
            suggestions.append(f"Why did {metric.lower()} change?")
            suggestions.append(
                f"Show {metric.lower()} trend over the last 7 days"
            )

    # -----------------------------
    # TREND → explanation or summary
    # -----------------------------
    elif intent == Intent.TREND:
        if metric:
            suggestions.append(f"Why did {metric.lower()} change recently?")
        suggestions.append("Give me a summary for today")

    return suggestions[:2]
