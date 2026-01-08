# Conversational Analytics Engine

A Safe, Explainable "Chat with Data" System

## Overview

This project is a conversational analytics engine that allows users to query business metrics using natural language while ensuring correctness, explainability, and trust.

Unlike typical "chat with data" demos, this system:

- ✅ Uses deterministic analytics logic for all calculations
- ✅ Uses LLMs only for intent classification and explanation phrasing
- ✅ Enforces causal reasoning via an explicit causal graph
- ✅ Never hallucinates metrics, numbers, or causes
- ✅ Gracefully handles missing or unsupported data

The result is a chatbot that behaves like a real BI analyst, not a guessing model.

## 🎯 Core Capabilities

### ✅ Metric Queries

Ask for the value of a metric at a specific time.

**Examples:**
- "What was revenue yesterday?"
- "How was conversion rate day before yesterday?"

### ✅ Comparisons (Point-in-Time)

Compare a metric across two specific periods.

**Examples:**
- "Compare traffic today vs yesterday"
- "Compare revenue yesterday vs day before"

### ✅ Trend Analysis

Analyze how a metric changes over time.

**Examples:**
- "Show revenue trend last 7 days"
- "How has traffic changed over time?"

### ✅ Performance Summaries

Get an executive-level summary across multiple KPIs.

**Examples:**
- "Give me a summary for today"
- "How did we perform yesterday?"
- "How did we perform last week?"

**Supports:**
- Daily summaries (day-over-day)
- Weekly aggregated summaries (explicit aggregation rules)

### ✅ Root Cause Analysis (Daily)

Explain why a metric changed on a specific day.

**Examples:**
- "Why did revenue drop yesterday?"
- "Why did traffic spike today?"

**Uses:**
- Deterministic metric deltas
- Directional alignment
- Causal graph constraints
- LLM only for narrative explanation

### ✅ Root Cause Analysis (Weekly / Aggregated)

Explain why an entire period (e.g. last week) performed worse.

**Examples:**
- "Why did last week perform worse?"
- "What went wrong last week?"

This is implemented as a hybrid flow:
- Weekly aggregation (deterministic)
- Week-over-week comparison
- Identification of top negative contributors
- Causal explanation using the same safe pipeline

## 🧠 Design Philosophy

### Deterministic First, LLM Last

| Component | Responsibility |
|-----------|---------------|
| Data Store | Source of truth |
| Query Planner | Deterministic execution plan |
| Aggregation Logic | Explicit math rules |
| Causal Graph | Allowed causal paths |
| LLM | Language only (no math, no guessing) |

**LLMs never:**
- ❌ Compute numbers
- ❌ Query data
- ❌ Decide causality
- ❌ Invent metrics

## 🏗️ Architecture

```
User Question
     ↓
Intent Classifier (LLM, constrained)
     ↓
Query Planner (deterministic)
     ↓
Data Store (Pandas / CSV)
     ↓
Aggregation & Comparison Logic
     ↓
Causal Reasoning (Graph-constrained)
     ↓
LLM (Explanation phrasing only)
     ↓
Final Answer
```

## 📁 Project Structure

```
dashboard-chatbot/
│
├── chatbot.py              # CLI entry point
├── intent_classifier.py    # Intent detection (LLM, constrained)
├── query_planner.py        # Deterministic query planning
├── data_store.py           # Pandas-backed metrics store
├── response_builder.py     # Core business logic + explanations
├── threshold_event.py      # Event model for root cause analysis
│
├── data/
│   └── metrics.csv         # Example dataset
│
├── causal_graph.yaml       # Explicit causal relationships
│
├── llm/
│   └── ollama_client.py    # LLM interface (timeout-safe)
│
├── utils/
│   ├── context_builder.py  # Builds context for explanations
│   ├── explainer.py       # LLM explanation generation
│   ├── fallback.py        # Fallback explanations
│   └── prompt.py          # LLM prompt guardrails
│
└── README.md
```

## 📊 Dataset Expectations

The system expects a tabular dataset with:

- A `date` column (ISO format: YYYY-MM-DD)
- One column per metric

**Example:**

```csv
date,Revenue,Traffic,Conversion Rate,Orders
2024-09-25,113200,44800,2.68,1201
2024-09-26,114600,45200,2.7,1220
...
```

**Supported Metrics:**
- Revenue
- Traffic
- Conversion Rate
- Orders
- Average Order Value

## 🔗 Causal Graph

Causality is explicitly defined in `causal_graph.yaml`. The LLM cannot reference causes outside this graph.

**Example:**

```yaml
Revenue:
  causes:
    - Average Revenue Per User
    - Activated Users
```

This ensures that root cause explanations are grounded in predefined relationships, preventing hallucination.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running locally
- Mistral 7B model (or compatible model) available in Ollama

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "dashboard chatbot"
```

2. Install dependencies:
```bash
pip install pandas requests pyyaml
```

3. Ensure Ollama is running:
```bash
ollama serve
```

4. Pull the required model (if not already available):
```bash
ollama pull mistral:7b-instruct
```

### Running the Chatbot

```bash
python chatbot.py
```

**Example session:**

```
You: show revenue trend last 7 days
Bot: Revenue shows a downward trend over the last 7 days with a change of 26.5%.

You: why did last week perform worse?
Bot: Last week's performance declined primarily due to a drop in Revenue...
```

## 🛡️ Safety & Guardrails

This system explicitly prevents:

- ❌ Metric hallucination
- ❌ Silent aggregation assumptions
- ❌ Causal overclaiming
- ❌ LLM-driven calculations
- ❌ Unsupported period guessing

If a query cannot be answered safely, the chatbot refuses gracefully.

## 🚀 Why This Is Different

**Most "chat with data" tools:**
- Let the LLM guess
- Mix reasoning and math
- Hallucinate causes
- Break silently on edge cases

**This system:**
- Treats analytics as engineering, not prompting
- Makes all assumptions explicit
- Is auditable, debuggable, and extensible

## 🔮 Future Extensions

- Conversational memory (safe follow-ups)
- Monthly / custom range summaries
- Visualizations + chat
- Slack / Web deployment
- Confidence scoring per explanation

## 🏁 Summary

This project demonstrates how to build a trustworthy conversational analytics system by combining:

- Deterministic data pipelines
- Explicit causal reasoning
- Carefully constrained LLM usage

It is designed to scale from a local CLI to production BI environments without sacrificing correctness.

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]