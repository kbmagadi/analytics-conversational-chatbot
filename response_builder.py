# chatbot/response_builder.py
from pathlib import Path
from intent_classifier import Intent
from threshold_event import ThresholdEvent
from utils.context_builder import build_context
from utils.prompt import build_prompt
from utils.explainer import generate_explanation
from datetime import timedelta 
from utils.fallback import fallback_explanation
from causal_graph import CausalGraph

print("📦 LOADED response_builder FROM:", __file__)

# -----------------------------
# Constants & config
# -----------------------------

AGGREGATION_RULES = {
    "Revenue": "sum",
    "Orders": "sum",
    "Traffic": "sum",
    "Conversion Rate": "avg",
}

def _get_aggregation_rule(metric: str, default: str = "sum") -> str:
    """
    Determine aggregation rule based on metric name/type.
    This provides intelligent defaults for metrics not in AGGREGATION_RULES.
    
    Args:
        metric: The metric name to determine aggregation for
        default: Default aggregation if no pattern matches
    
    Returns:
        "sum" or "avg" based on metric characteristics
    """
    metric_lower = metric.lower()
    
    # Rate/percentage metrics should be averaged
    if any(word in metric_lower for word in ["rate", "ratio", "percent", "%", "percentage"]):
        return "avg"
    
    # Count metrics should be summed
    if any(word in metric_lower for word in ["count", "orders", "users", "visits", "sessions", "clicks"]):
        return "sum"
    
    # Revenue/money metrics should be summed
    if any(word in metric_lower for word in ["revenue", "sales", "cost", "price", "amount", "value"]):
        return "sum"
    
    # Average/mean metrics should be averaged
    if any(word in metric_lower for word in ["average", "avg", "mean", "aov"]):
        return "avg"
    
    # Default from hardcoded rules if exists
    if metric in AGGREGATION_RULES:
        return AGGREGATION_RULES[metric]
    
    # Fallback to default
    return default

def _format_number(value: float) -> str:
    """
    Format numbers nicely for display.
    
    Args:
        value: The numeric value to format
    
    Returns:
        Formatted string representation
    """
    if isinstance(value, float):
        # For large numbers, use comma separators
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        # For small numbers, show 2 decimal places
        elif abs(value) < 1:
            return f"{value:.4f}"
        # For medium numbers, show 2 decimal places
        else:
            return f"{value:.2f}"
    return str(value)

GRAPH = CausalGraph()
KPIS = GRAPH.metrics()

CAUSAL_GRAPH_YAML = Path("causal_graph.yaml").read_text()

# -----------------------------
# Public entry point
# -----------------------------

def build_response(intent: Intent, query_plan: dict, metrics_store, summary_context=None):
    """
    Build the final chatbot response with better error handling.
    """
    if query_plan.get("unsupported") == "forecast":
        return (
            "I currently analyze historical data and don't generate future projections. "
            "You can ask about recent trends, summaries, or why metrics changed."
        )
    
    try:
        if intent == Intent.VALUE:
            return _handle_value(query_plan, metrics_store, summary_context)

        if intent == Intent.COMPARISON:
            return _handle_comparison(query_plan, metrics_store)

        if intent == Intent.TREND:
            return _handle_trend(query_plan, metrics_store)

        if intent == Intent.SUMMARY:
            return _handle_summary(query_plan, metrics_store, summary_context)

        if intent == Intent.ROOT_CAUSE:
            return _handle_root_cause(query_plan, metrics_store)

        if intent == Intent.PERIOD_ROOT_CAUSE:
            return _handle_period_root_cause(query_plan, metrics_store)

        return _handle_unknown()
        
    except ValueError as e:
        # Enhanced error messages with suggestions
        error_msg = str(e)
        
        # Add helpful suggestions based on error type
        if "metric" in error_msg.lower() and "not found" in error_msg.lower():
            available = list(metrics_store.df.columns)
            available = [m for m in available if m != "date"]
            suggestions = f"Available metrics: {', '.join(available[:5])}"
            return f"⚠️ {error_msg}\n💡 {suggestions}"
        
        if "period" in error_msg.lower() and "not specified" in error_msg.lower():
            return f"⚠️ {error_msg}\n💡 Try: 'today', 'yesterday', 'last week', or a specific date."
        
        return f"⚠️ {error_msg}"
        
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"DEBUG: {traceback.format_exc()}")
        return f"⚠️ I ran into an issue: {str(e)}. Please try rephrasing or be more specific."

# --------------------------------------------------
# Intent handlers
# --------------------------------------------------

def _handle_value(plan, store, summary_ctx=None):
    print("🔥 ENTERED _handle_value")
    print("PLAN:", plan)

    metric = plan.get("metric")
    period = plan.get("period")

    # -----------------------------
    # HARD GUARDS
    # -----------------------------
    if not metric:
        raise ValueError("Please specify which metric you want.")

    if period is None:
        raise ValueError(
            "Please specify a time period (e.g., today or yesterday)."
        )

    # ✅ NORMALIZE PERIOD
    if period == "today":
        period = "latest"

    if period in {"last_week", "last_7_days"}:
        raise ValueError(
            f"{metric} for {period.replace('_', ' ')} is an aggregated value. "
            "Try asking for a summary instead."
        )

    # -----------------------------
    # Cached summary fast-path
    # -----------------------------
    if summary_ctx and summary_ctx.can_answer_value(metric, period):
        value = summary_ctx.get_value(metric, period)
        value_str = _format_number(value)
        return f"{metric} for {period.replace('_', ' ')} is {value_str}."

    # -----------------------------
    # Raw datastore fallback
    # -----------------------------
    value = store.get_value(metric, period)
    value_str = _format_number(value)
    return f"{metric} for {period.replace('_', ' ')} is {value_str}."


def _handle_comparison(plan, store):
    metric = plan["metric"]
    period = plan["period"]
    compare_to = plan.get("compare_to")

    if not compare_to:
        raise ValueError("Comparison period not specified.")

    values = store.get_comparison(metric, period, compare_to)

    curr, base = values["current"], values["baseline"]
    change_pct = round(((curr - base) / base) * 100, 2) if base != 0 else 0.0
    direction = "increased" if change_pct > 0 else "decreased"
    
    # Format the values nicely
    curr_str = _format_number(curr)
    base_str = _format_number(base)

    return (
        f"{metric} {direction} by {abs(change_pct)}% "
        f"from {base_str} ({compare_to.replace('_', ' ')}) "
        f"to {curr_str} ({period.replace('_', ' ')})."
    )


def _handle_trend(plan, store):
    metric = plan["metric"]
    period = plan["period"]

    if not metric:
        raise ValueError(
            "Please specify which metric you want to analyze (e.g., revenue or traffic)."
        )

    df = store.get_series(metric, period)
    start, end = df.iloc[0][metric], df.iloc[-1][metric]

    change_pct = round(((end - start) / start) * 100, 2) if start != 0 else 0.0
    direction = "upward" if change_pct > 0 else "downward"
    
    # Format values
    start_str = _format_number(start)
    end_str = _format_number(end)

    return (
        f"{metric} shows a {direction} trend over the "
        f"{period.replace('_', ' ')} with a change of {abs(change_pct)}% "
        f"(from {start_str} to {end_str})."
    )


# -----------------------------
# SUMMARY (daily + weekly)
# -----------------------------

def _handle_summary(plan, store, summary_ctx=None):
    period = plan["period"]
    compare_to = plan.get("compare_to")

    # ---- Fast path: cached daily summary ----
    if summary_ctx and summary_ctx.can_answer_summary(period):
        daily = summary_ctx.get_summary()

        parts = []
        for metric, info in daily.items():
            direction = "up" if info["change_pct"] > 0 else "down"
            parts.append(f"{metric} was {direction} {abs(info['change_pct'])}%")

        return (
            f"Here's a summary for {period.replace('_', ' ')}: "
            + "; ".join(parts[:3]) + "."
        )

    # ---- Weekly / range-based summary (narrative) ----
    if period == "last_week":
        # Get available metrics from store (only process metrics that exist in data)
        available_metrics = [col for col in store.df.columns if col != "date"]
        # Intersect with KPIS to only use metrics that exist in both graph and data
        metrics_to_process = [m for m in KPIS if m in available_metrics]
        
        # If no overlap, fall back to available metrics
        if not metrics_to_process:
            metrics_to_process = available_metrics

        # BATCH PROCESSING: Process all metrics efficiently
        signals = []
        for metric in metrics_to_process:
            agg = _get_aggregation_rule(metric)
            try:
                last = store.get_aggregate_range(metric, 6, 0, agg)
                prev = store.get_aggregate_range(metric, 13, 7, agg)

                change_pct = (
                    round(((last - prev) / prev) * 100, 2)
                    if prev != 0 else 0.0
                )

                signals.append({
                    "metric": metric,
                    "change_pct": change_pct
                })

            except (ValueError, KeyError):
                continue

        if not signals:
            raise ValueError("Not enough data to summarize last week.")

        negatives = [s for s in signals if s["change_pct"] < 0]
        positives = [s for s in signals if s["change_pct"] > 0]

        negatives.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        positives.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

        summary_context = {
            "period": "last week",
            "declines": negatives[:2],
            "improvements": positives[:2]
        }

        prompt = f"""
    You are an analytics assistant summarizing performance.

    Use ONLY the information below.
    Do NOT invent metrics or numbers.

    Period: {summary_context['period']}

    Declining metrics:
    {summary_context['declines']}

    Improving metrics:
    {summary_context['improvements']}

    Write a 2–3 sentence executive summary.
    """

        try:
            explanation = generate_explanation(prompt)
            if explanation:
                return explanation
        except Exception:
            pass

    # ---- Daily comparison summary ----
    if not compare_to:
        raise ValueError("Not enough data to summarize performance.")

    # Get available metrics from store (only process metrics that exist in data)
    available_metrics = [col for col in store.df.columns if col != "date"]
    # Intersect with KPIS to only use metrics that exist in both graph and data
    metrics_to_process = [m for m in KPIS if m in available_metrics]

    # If no overlap, fall back to available metrics
    if not metrics_to_process:
        metrics_to_process = available_metrics

    # BATCH PROCESSING: Use list comprehension for faster processing
    changes = []
    for metric in metrics_to_process:
        try:
            values = store.get_comparison(metric, period, compare_to)
            curr, base = values["current"], values["baseline"]
            change_pct = round(((curr - base) / base) * 100, 2) if base != 0 else 0.0
            changes.append({"metric": metric, "change_pct": change_pct})
        except (ValueError, KeyError):
            continue

    if not changes:
        raise ValueError("Not enough data to summarize performance.")

    changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    summary = []
    for c in changes[:3]:
        direction = "up" if c["change_pct"] > 0 else "down"
        summary.append(f"{c['metric']} was {direction} {abs(c['change_pct'])}%")

    return (
        f"Here's a summary for {period.replace('_', ' ')}: "
        + "; ".join(summary) + "."
    )


# -----------------------------
# ROOT CAUSE (daily)
# -----------------------------

def _handle_root_cause(plan, store):
    """
    Enhanced root cause with intelligent defaults.
    """
    metric = plan.get("metric")
    period = plan.get("period")
    compare_to = plan.get("compare_to")
    
    # Intelligent defaults
    if not metric:
        # Try to infer from context or use most recent changed metric
        if hasattr(store, 'graph'):
            metrics = store.graph.metrics()
            # Use first available metric as fallback
            metric = metrics[0] if metrics else None
    
    if not period:
        period = "latest"
    elif period == "today":
        period = "latest"
    
    if not compare_to:
        # Smart defaults based on period
        if period == "latest":
            compare_to = "yesterday"
        elif period == "yesterday":
            compare_to = "day_before"
        else:
            # Try to find a reasonable comparison
            try:
                period_date = store._resolve_period(period)
                compare_to_date = period_date - timedelta(days=1)
                # Find closest available date
                available_dates = sorted(store.df["date"].unique())
                compare_to = available_dates[-2] if len(available_dates) >= 2 else None
            except:
                compare_to = None
    
    if not compare_to:
        raise ValueError(
            "Not enough historical data to explain the change. "
            "Please specify a comparison period (e.g., 'yesterday' or 'today')."
        )
    target = store.get_comparison(metric, period, compare_to)

    supporting_metrics = {}
    for col in store.df.columns:
        if col in {"date", metric}:
            continue
        try:
            supporting_metrics[col] = store.get_comparison(col, period, compare_to)
        except ValueError:
            continue

    event = ThresholdEvent(
        rule_name=f"{metric} Change Explanation",
        metric=metric,
        current_value=target["current"],
        baseline_value=target["baseline"],
        threshold_type="CHAT_QUERY",
        threshold_value=0,
        time_window=f"{period.replace('_', ' ')} vs {compare_to.replace('_', ' ')}",
        supporting_metrics=supporting_metrics,
        causal_graph_yaml=CAUSAL_GRAPH_YAML,
    )

    return _explain_event(event)


# -----------------------------
# ROOT CAUSE (weekly / period)
# -----------------------------

def _handle_period_root_cause(plan, store):
    # Get available metrics from store (only process metrics that exist in data)
    available_metrics = [col for col in store.df.columns if col != "date"]
    # Intersect with KPIS to only use metrics that exist in both graph and data
    metrics_to_process = [m for m in KPIS if m in available_metrics]
    
    # If no overlap, fall back to available metrics
    if not metrics_to_process:
        metrics_to_process = available_metrics

    # BATCH PROCESSING: Process all metrics efficiently
    changes = []
    for metric in metrics_to_process:
        agg = _get_aggregation_rule(metric)
        try:
            last = store.get_aggregate_range(metric, 6, 0, agg)
            prev = store.get_aggregate_range(metric, 13, 7, agg)

            change_pct = round(((last - prev) / prev) * 100, 2) if prev != 0 else 0.0
            changes.append({"metric": metric, "change_pct": change_pct})
        except (ValueError, KeyError):
            continue

    if not changes:
        raise ValueError("Not enough data to analyze last week's performance.")

    negatives = [c for c in changes if c["change_pct"] < 0]
    negatives.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    if not negatives:
        return "Last week did not perform worse compared to the previous week."

    primary = negatives[0]["metric"]

    supporting_metrics = {
        c["metric"]: {"current": c["change_pct"], "baseline": 0}
        for c in negatives[1:4]
    }

    event = ThresholdEvent(
        rule_name="Weekly Performance Decline",
        metric=primary,
        current_value=negatives[0]["change_pct"],
        baseline_value=0,
        threshold_type="WEEKLY_DECLINE",
        threshold_value=0,
        time_window="Last week vs previous week",
        supporting_metrics=supporting_metrics,
        causal_graph_yaml=CAUSAL_GRAPH_YAML,
    )

    return _explain_event(event)


# -----------------------------
# Shared explanation helper
# -----------------------------

def _explain_event(event):
    context = build_context(event)
    prompt = build_prompt(context)

    try:
        explanation = generate_explanation(prompt)
        if explanation:
            return explanation
    except Exception:
        pass

    return fallback_explanation(context)

def _weekly_summary_signals(store):
    # Get available metrics from store (only process metrics that exist in data)
    available_metrics = [col for col in store.df.columns if col != "date"]
    # Intersect with KPIS to only use metrics that exist in both graph and data
    metrics_to_process = [m for m in KPIS if m in available_metrics]
    
    # If no overlap, fall back to available metrics
    if not metrics_to_process:
        metrics_to_process = available_metrics

    # BATCH PROCESSING: Process all metrics efficiently
    signals = []
    for metric in metrics_to_process:
        agg = _get_aggregation_rule(metric)
        try:
            last = store.get_aggregate_range(metric, 6, 0, agg)
            prev = store.get_aggregate_range(metric, 13, 7, agg)

            change_pct = (
                round(((last - prev) / prev) * 100, 2)
                if prev != 0 else 0.0
            )

            signals.append({
                "metric": metric,
                "change_pct": change_pct
            })

        except (ValueError, KeyError):
            continue

    return signals

def _handle_unknown():
    return (
        "I'm not sure how to answer that yet. "
        "Try asking about a specific metric, comparison, trend, or root cause."
    )