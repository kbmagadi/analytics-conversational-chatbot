from llm.ollama_client import call_llm

def generate_explanation(prompt: str) -> str:
    print("LLM CALLED")

    response = call_llm(
        prompt=prompt,
        temperature=0.2
    )

    return response.strip()
