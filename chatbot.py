# chatbot/chatbot.py

from intent_classifier import classify_intent
from query_planner import plan_query
from response_builder import build_response
from data_store import MetricsStore
from followups import suggest_followups
from summary_context import SummaryContext
from memory import ConversationMemory


def run_chatbot():
    """
    CLI entry point for chatting with the dataset.
    """
    print("=" * 60)
    print("📊 Analytics Chatbot")
    print("Ask questions about your metrics. Type 'exit' to quit.")
    print("=" * 60)

    # --------------------------------------------------
    # Initialize core components (once per session)
    # --------------------------------------------------
    metrics_store = MetricsStore()
    summary_ctx = SummaryContext(metrics_store)
    memory = ConversationMemory()
    print("\n📌 Loaded Summary Context (cached):")
    print("-" * 40)

    for metric, info in summary_ctx.get_summary().items():
        direction = "up" if info["change_pct"] > 0 else "down"
        print(
            f"{metric}: {info['current']} "
            f"({direction} {abs(info['change_pct'])}%)"
        )

    print("-" * 40)


    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                print("\n👋 Exiting chatbot. Goodbye!")
                break

            # --------------------------------------------------
            # Step 1: Intent classification (LLM, shallow)
            # --------------------------------------------------
            intent = classify_intent(user_input)
            print("Intent:", intent)

            # --------------------------------------------------
            # Step 2: Query planning (deterministic)
            # --------------------------------------------------
            query_plan = plan_query(
                user_input=user_input,
                intent=intent
            )

            # --------------------------------------------------
            # Step 3: Resolve follow-ups using memory (SAFE)
            # --------------------------------------------------
            resolved_plan = memory.resolve(intent, query_plan)

            # --------------------------------------------------
            # Step 4: Build grounded response
            # (deterministic analytics + constrained LLM)
            # --------------------------------------------------
            response = build_response(
                intent=intent,
                query_plan=resolved_plan,
                metrics_store=metrics_store,
                summary_context=summary_ctx
            )

            print(f"\nBot: {response}")

            # --------------------------------------------------
            # Step 5: Update memory AFTER successful resolution
            # --------------------------------------------------
            memory.update(intent, resolved_plan)

            # --------------------------------------------------
            # Step 6: Suggested follow-ups
            # --------------------------------------------------
            followups = suggest_followups(intent, resolved_plan)

            if followups:
                print("\nSuggested follow-ups:")
                for f in followups:
                    print(f"• {f}")

        except KeyboardInterrupt:
            print("\n\n👋 Chatbot interrupted. Exiting.")
            break

        except Exception as e:
            print("\n⚠️ Something went wrong.")
            print(f"Error: {e}")
            print("Try rephrasing your question.")


if __name__ == "__main__":
    run_chatbot()
