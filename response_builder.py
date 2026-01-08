# chatbot/response_builder.py

from pathlib import Path

from intent_classifier import Intent
from threshold_event import ThresholdEvent
from utils.context_builder import build_context
from utils.prompt import build_prompt
from utils.explainer import generate_explanation
from utils.fallback import fallback_explanation


# -----------------------------
# Constants & config
# -----------------------------

AGGREGATION_RULES = {
    "Revenue": "sum",
    "Orders": "sum",
    "Traffic": "sum",
    "Conversion Rate": "avg",
}

KPIS = ["Revenue", "Traffic", "Conversion Rate", "Orders"]

CAUSAL_GRAPH_YAML = Path("causal_graph.yaml").read_text()


# -----------------------------
# Public entry point
# -----------------------------

def build_response(intent: Intent, query_plan: dict, metrics_store, summary_context=None):
    """
    Build the final chatbot response based on intent and query plan.
    """
    if query_plan.get("unsupported") == "forecast":
        return (
            "I currently analyze historical data and don’t generate future projections. "
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
        return f"⚠️ {str(e)}"
    except Exception:
        return "⚠️ I ran into an issue while answering that. Please try rephrasing."


# --------------------------------------------------
# Intent handlers
# --------------------------------------------------

def _handle_value(plan, store, summary_ctx=None):
    metric = plan["metric"]
    period = plan["period"]

    if summary_ctx and summary_ctx.can_answer_value(metric, period):
        value = summary_ctx.get_value(metric)
        return f"{metric} for {period.replace('_', ' ')} is {value}."

    value = store.get_value(metric, period)
    return f"{metric} for {period.replace('_', ' ')} is {value}."


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

    return (
        f"{metric} {direction} by {abs(change_pct)}% "
        f"from {compare_to.replace('_', ' ')} to {period.replace('_', ' ')}."
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

    return (
        f"{metric} shows a {direction} trend over the "
        f"{period.replace('_', ' ')} with a change of {abs(change_pct)}%."
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
            f"Here’s a summary for {period.replace('_', ' ')}: "
            + "; ".join(parts[:3]) + "."
        )

    # ---- Weekly / range-based summary ----
    # ---- Weekly / range-based summary (narrative) ----
    if period == "last_week":
        signals = []

        for metric, agg in AGGREGATION_RULES.items():
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

            except ValueError:
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

    changes = []

    for metric in KPIS:
        try:
            values = store.get_comparison(metric, period, compare_to)
            curr, base = values["current"], values["baseline"]
            change_pct = round(((curr - base) / base) * 100, 2) if base != 0 else 0.0
            changes.append({"metric": metric, "change_pct": change_pct})
        except ValueError:
            continue

    if not changes:
        raise ValueError("Not enough data to summarize performance.")

    changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    summary = []
    for c in changes[:3]:
        direction = "up" if c["change_pct"] > 0 else "down"
        summary.append(f"{c['metric']} was {direction} {abs(c['change_pct'])}%")

    return (
        f"Here’s a summary for {period.replace('_', ' ')}: "
        + "; ".join(summary) + "."
    )


# -----------------------------
# ROOT CAUSE (daily)
# -----------------------------

def _handle_root_cause(plan, store):
    metric = plan["metric"]
    period = plan["period"]
    compare_to = plan.get("compare_to")

    if not compare_to:
        raise ValueError("Not enough historical data to explain the change.")

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
    changes = []

    for metric in KPIS:
        agg = AGGREGATION_RULES[metric]
        try:
            last = store.get_aggregate_range(metric, 6, 0, agg)
            prev = store.get_aggregate_range(metric, 13, 7, agg)

            change_pct = round(((last - prev) / prev) * 100, 2) if prev != 0 else 0.0
            changes.append({"metric": metric, "change_pct": change_pct})
        except ValueError:
            continue

    if not changes:
        raise ValueError("Not enough data to analyze last week’s performance.")

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
    signals = []

    for metric, agg in AGGREGATION_RULES.items():
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

        except ValueError:
            continue

    return signals

def _handle_unknown():
    return (
        "I’m not sure how to answer that yet. "
        "Try asking about a specific metric, comparison, trend, or root cause."
    )
