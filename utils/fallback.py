def fallback_explanation(context: dict) -> str:
    print("FALLBACK CALLED")
    return (
        f"{context['alert']['metric']} breached the configured threshold. "
        f"Current value is {context['values']['current']} compared to "
        f"{context['values']['baseline']} in the previous period."
    )
