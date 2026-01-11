# test_chatbot.py

from intent_classifier import Intent, classify_intent
from query_planner import plan_query
from response_builder import build_response
from data_store import MetricsStore
from summary_context import SummaryContext
from memory import ConversationMemory

test_cases = [
    # (query, expected_intent, should_succeed)
    ("What is revenue today?", Intent.VALUE, True),
    ("Compare revenue today vs yesterday", Intent.COMPARISON, True),
    ("Show traffic trend for last 7 days", Intent.TREND, True),
    ("Give me a summary for today", Intent.SUMMARY, True),
    ("Why did revenue change recently?", Intent.ROOT_CAUSE, True),
    ("Why was last week bad?", Intent.PERIOD_ROOT_CAUSE, True),
    ("What is profit today?", Intent.VALUE, False),  # Invalid metric
    ("revenue", Intent.VALUE, False),  # Missing period
    ("What will revenue be next week?", Intent.UNKNOWN, True),  # Future
]

def run_tests():
    print("=" * 60)
    print("🧪 Running Chatbot Tests")
    print("=" * 60)
    
    try:
        # Initialize chatbot components
        print("\n📦 Initializing components...")
        metrics_store = MetricsStore()
        summary_ctx = SummaryContext(metrics_store)
        memory = ConversationMemory()
        print("✅ Components initialized successfully\n")
        
    except Exception as e:
        print(f"❌ Failed to initialize components: {e}")
        import traceback
        traceback.print_exc()
        return
    
    passed = 0
    failed = 0
    
    for i, (query, expected_intent, should_succeed) in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_cases)}: {query}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Intent classification
            intent = classify_intent(query)
            print(f"Intent: {intent} (expected: {expected_intent})")
            
            # Step 2: Query planning
            query_plan = plan_query(query, intent, metrics_store)
            print(f"Query Plan: {query_plan}")
            
            # Step 3: Build response
            response = build_response(intent, query_plan, metrics_store, summary_ctx)
            
            # Step 4: Evaluate result
            is_success = not response.startswith('⚠️') if should_succeed else response.startswith('⚠️')
            intent_correct = intent == expected_intent
            
            print(f"Response: {response[:150]}{'...' if len(response) > 150 else ''}")
            print(f"Intent Match: {'✅' if intent_correct else '❌'}")
            print(f"Success Check: {'✅' if is_success else '❌'} (expected {'success' if should_succeed else 'error'})")
            
            if intent_correct and is_success:
                passed += 1
                print("✅ TEST PASSED")
            else:
                failed += 1
                print("❌ TEST FAILED")
                
        except Exception as e:
            failed += 1
            print(f"❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {len(test_cases)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    run_tests()