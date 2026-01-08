# chatbot/intent_classifier.py

from enum import Enum
from llm.ollama_client import call_llm


class Intent(str, Enum):
    VALUE = "VALUE"             # single metric value
    COMPARISON = "COMPARISON"   # compare two periods
    TREND = "TREND"             # time series / trend
    ROOT_CAUSE = "ROOT_CAUSE"   # why did something change
    SUMMARY = "SUMMARY"
    PERIOD_ROOT_CAUSE = "PERIOD_ROOT_CAUSE"  
    UNKNOWN = "UNKNOWN"

INTENT_PROMPT = """
You are an intent classifier for an analytics chatbot.

Your job is to classify the user's question into EXACTLY ONE of the intents below.

INTENTS:

VALUE
→ Asking for the value of a single metric at a specific point in time
→ Examples: today, yesterday, day before yesterday

COMPARISON
→ Comparing a single metric between two specific points in time
→ Examples: today vs yesterday, yesterday vs day before

TREND
→ Asking about how a metric changes over a time range
→ Examples: last 7 days, trend, over time

SUMMARY
→ Asking for an overall performance summary across multiple metrics
→ Examples: how did we perform, give me a summary, overall performance

ROOT_CAUSE
→ Asking why a single metric changed at a specific point in time
→ Examples: why did revenue drop yesterday, why did traffic spike today

PERIOD_ROOT_CAUSE
→ Asking why performance over an aggregated period (like last week) was good or bad
→ Examples: why was last week bad, what went wrong last week

UNKNOWN
→ Anything that does not clearly fit the above categories

RULES:
- Respond with ONLY the intent label
- Do NOT explain
- Do NOT add punctuation
- Do NOT add extra words
- Choose the MOST specific intent

EXAMPLES:
"What is revenue today?" → VALUE
"How was our conversion rate yesterday?" → VALUE
"What was traffic day before yesterday?" → VALUE

"Compare revenue today vs yesterday" → COMPARISON
"Compare traffic yesterday vs day before" → COMPARISON

"Show traffic trend for last 7 days" → TREND
"How has revenue changed over time?" → TREND

"Give me a summary for today" → SUMMARY
"How did we perform yesterday?" → SUMMARY
"Overall performance yesterday?" → SUMMARY

"Why did revenue drop yesterday?" → ROOT_CAUSE
"Why did traffic spike today?" → ROOT_CAUSE

"Why was last week bad?" → PERIOD_ROOT_CAUSE
"Why did last week perform worse?" → PERIOD_ROOT_CAUSE
"What went wrong last week?" → PERIOD_ROOT_CAUSE

"How did we perform?" → UNKNOWN
"""

def classify_intent(user_query: str) -> Intent:
    """
    Classifies user query into a predefined intent.
    """
    prompt = f"""
{INTENT_PROMPT}

User Question:
{user_query}
"""

    try:
        response = call_llm(
            prompt=prompt,
            temperature=0.0   # IMPORTANT: deterministic
        )

        intent_str = response.strip().upper()

        if intent_str in Intent.__members__:
            return Intent[intent_str]

        return Intent.UNKNOWN

    except Exception:
        return Intent.UNKNOWN
