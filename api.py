# api.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    reply: str
    followups: List[str]

from intent_classifier import classify_intent
from query_planner import plan_query
from response_builder import build_response
from followups import suggest_followups
from data_store import MetricsStore
from memory import ConversationMemory
from summary_context import SummaryContext

app = FastAPI(title="Dashboard Chatbot API")

metrics_store = MetricsStore()
summary_ctx = SummaryContext(metrics_store)
memory = ConversationMemory()

@app.on_event("startup")
def startup():
    global metrics_store, memory, summary_ctx
    metrics_store = MetricsStore()
    memory = ConversationMemory()
    summary_ctx = SummaryContext(metrics_store)

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Dashboard Chatbot API is running",
        "docs": "/docs"
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user_query = request.message
    session_id = request.session_id

    # Store user message
    memory.add_user_message(session_id, user_query)

    # Core chatbot pipeline
    intent = classify_intent(user_query)
    plan = plan_query(
        user_query=user_query,
        intent=intent,
        store=metrics_store,
        summary_ctx=summary_ctx
    )

    response_text = build_response(
        plan=plan,
        store=metrics_store,
        memory=memory,
        summary_ctx=summary_ctx
    )

    followups = suggest_followups(plan)

    # Store assistant reply
    memory.add_assistant_message(session_id, response_text)

    return {
        "reply": response_text,
        "followups": followups
    }
