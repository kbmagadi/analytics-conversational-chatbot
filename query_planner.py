# chatbot/query_planner.py

from intent_classifier import Intent

FUTURE_KEYWORDS = {
    "next week", "next month", "forecast", "projected",
    "prediction", "expected growth"
}

SUPPORTED_METRICS = [
    "Revenue",
    "Conversion Rate",
    "Traffic",
    "Orders",
    "Average Order Value"
]


def contains_future_language(query: str) -> bool:
    q = query.lower()
    return any(k in q for k in FUTURE_KEYWORDS)

# query_planner.py

from difflib import get_close_matches

def extract_metric(user_query: str, available_metrics: list = None) -> str | None:
    """
    Extract metric with fuzzy matching against available metrics.
    """
    if available_metrics is None:
        # Fallback to hardcoded list if not provided
        available_metrics = SUPPORTED_METRICS
    
    query = user_query.lower()
    
    # First try exact aliases
    aliases = {
        "conversion rate": "Conversion Rate",
        "aov": "Average Order Value",
        "avg order value": "Average Order Value",
        "orders": "Orders",
        "revenue": "Revenue",
        "traffic": "Traffic"
    }
    
    for alias, metric in aliases.items():
        if alias in query and metric in available_metrics:
            return metric
    
    # Fuzzy matching: find closest metric name
    query_words = set(query.split())
    best_match = None
    best_score = 0
    
    for metric in available_metrics:
        metric_lower = metric.lower()
        # Check if any word in query matches metric
        for word in query_words:
            if word in metric_lower or metric_lower in word:
                score = len(word) / len(metric_lower)
                if score > best_score:
                    best_score = score
                    best_match = metric
    
    # Use difflib for fuzzy string matching
    if not best_match:
        matches = get_close_matches(query, [m.lower() for m in available_metrics], n=1, cutoff=0.6)
        if matches:
            idx = [m.lower() for m in available_metrics].index(matches[0])
            best_match = available_metrics[idx]
    
    return best_match

# query_planner.py

from llm.ollama_client import call_llm
from datetime import datetime, timedelta

def extract_time_range_llm(user_query: str, latest_date: datetime = None) -> dict:
    """
    Use LLM to extract time periods more flexibly.
    Falls back to rule-based if LLM fails.
    """
    if latest_date is None:
        latest_date = datetime.now()
    
    prompt = f"""
Extract time period information from this query. Return JSON with "period" and optionally "compare_to".

Available periods: "latest" (today), "yesterday", "day_before", "last_7_days", "last_week"
For comparisons, use: "yesterday", "day_before", or relative days like "2_days_ago"

Query: "{user_query}"

Return ONLY valid JSON like {{"period": "latest", "compare_to": "yesterday"}} or {{"period": "yesterday"}}
If no time period found, return {{}}.
"""
    
    try:
        response = call_llm(prompt, temperature=0.0)
        # Try to parse JSON from response
        import json
        import re
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            result = json.loads(json_match.group())
            return result
    except Exception:
        pass
    
    # Fallback to rule-based
    return extract_time_range(user_query)

def extract_time_range(user_query: str) -> dict:
    """
    Enhanced rule-based extraction with more patterns.
    """
    q = user_query.lower()
    
    # Relative time patterns
    if any(word in q for word in ["recently", "recent", "lately", "just now"]):
        return {"period": "latest", "compare_to": "yesterday"}
    
    # Day patterns
    if "yesterday" in q:
        return {"period": "yesterday", "compare_to": "day_before"}
    
    if any(word in q for word in ["today", "now", "current"]):
        return {"period": "latest", "compare_to": "yesterday"}
    
    if "day before yesterday" in q or "2 days ago" in q:
        return {"period": "day_before"}
    
    # Week patterns
    if "last week" in q:
        return {"period": "last_week", "compare_to": "week_before"}
    
    if any(phrase in q for phrase in ["last 7 days", "past week", "7 days"]):
        return {"period": "last_7_days"}
    
    # Month patterns (if you add support)
    if "last month" in q:
        return {"period": "last_month", "compare_to": "month_before"}
    
    return {}

def plan_query(user_input: str, intent: Intent, metrics_store=None) -> dict:
    """
    Enhanced query planning with dynamic metric discovery and intelligent defaults.
    Converts (user_input, intent) into a deterministic query plan.
    """
    # Get available metrics from store if provided
    available_metrics = None
    if metrics_store:
        if hasattr(metrics_store, 'df'):
            # Get metrics from DataFrame (exclude date column)
            available_metrics = [col for col in metrics_store.df.columns if col != "date"]
        # Also check causal graph for additional metrics
        if hasattr(metrics_store, 'graph'):
            graph_metrics = metrics_store.graph.metrics()
            if available_metrics:
                available_metrics = list(set(available_metrics + graph_metrics))
            else:
                available_metrics = graph_metrics
    
    # Extract metric with fuzzy matching
    metric = extract_metric(user_input, available_metrics)
    
    # Extract time range (try LLM first, fallback to rule-based)
    time_info = extract_time_range(user_input)
    # Optionally use LLM-based extraction for more flexibility:
    # time_info = extract_time_range_llm(user_input, 
    #     latest_date=metrics_store.latest_date if metrics_store and hasattr(metrics_store, 'latest_date') else None)
    
    # Forecast guard
    if contains_future_language(user_input):
        return {
            "intent": intent,
            "unsupported": "forecast"
        }
    
    plan = {
        "intent": intent,
        "metric": metric
    }
    
    if "period" in time_info:
        plan["period"] = time_info["period"]
    
    if "compare_to" in time_info:
        plan["compare_to"] = time_info["compare_to"]
    
    return plan