# chatbot/query_planner.py

import re
from intent_classifier import Intent

FUTURE_KEYWORDS = {
    "next week", "next month", "forecast", "projected",
    "prediction", "expected growth"
}

def contains_future_language(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in FUTURE_KEYWORDS)

SUPPORTED_METRICS = [
    "Revenue",
    "Conversion Rate",
    "Traffic",
    "Orders",
    "Average Order Value"
]

def extract_metric(user_query: str) -> str | None:
    query = user_query.lower()

    for metric in SUPPORTED_METRICS:
        if metric.lower() in query:
            return metric

    # Common aliases (MVP)
    aliases = {
        "conversion rate": "Conversion Rate",
        "aov": "Average Order Value",
        "avg order value": "Average Order Value",
        "orders": "Orders",
        "revenue": "Revenue",
        "traffic": "Traffic"
    }

    for alias, metric in aliases.items():
        if alias in query:
            return metric

    return None

def extract_time_range(user_query: str) -> dict:
    """
    Extract time range information from user query.
    MVP supports only a few common patterns.
    """
    q = user_query.lower()

    if "yesterday" in q:
        return {
            "period": "yesterday",
            "compare_to": "day_before"
        }

    if "today" in q:
        return {
            "period": "today",
            "compare_to": "yesterday"
        }

    if "day before yesterday" in q:
        return {
            "period": "day_before"
        }

    if "last week" in q:
        return {
            "period": "last_week",
            "compare_to": "week_before"
        }

    if "last 7 days" in q:
        return {
            "period": "last_7_days"
        }

    # Default fallback
    return {
        "period": "latest"
    }


def plan_query(user_input: str, intent: Intent) -> dict:
    """
    Converts (user_input, intent) into a deterministic query plan.
    """
    metric = extract_metric(user_input)
    time_info = extract_time_range(user_input)

    if intent == Intent.VALUE:
        return {
            "intent": intent,
            "metric": metric,
            "period": time_info["period"]
        }

    if intent == Intent.COMPARISON:
        return {
            "intent": intent,
            "metric": metric,
            "period": time_info.get("period"),
            "compare_to": time_info.get("compare_to")
        }

    if contains_future_language(user_input):
        return {
            "intent": intent,
            "unsupported": "forecast"
        }

    if intent == Intent.TREND:
        return {
            "intent": intent,
            "metric": metric,
            "period": time_info["period"]
        }

    if intent == Intent.ROOT_CAUSE:
        return {
            "intent": intent,
            "metric": metric,
            "period": time_info.get("period"),
            "compare_to": time_info.get("compare_to")
        }

    if intent == Intent.SUMMARY:
        return {
            "intent": intent,
            "period": time_info.get("period", "latest"),
            "compare_to": time_info.get("compare_to", "yesterday")
        }

    if intent == Intent.PERIOD_ROOT_CAUSE:
        return {
            "intent": intent,
            "period": time_info.get("period", "last_week"),
            "compare_to": "week_before"
        }

    return {
        "intent": Intent.UNKNOWN
    }
