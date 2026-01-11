from functools import lru_cache
from llm.ollama_client import call_llm
import hashlib

# Cache explanations based on prompt hash
@lru_cache(maxsize=64)
def _cached_explanation(prompt_hash: str, prompt: str) -> str:
    """Internal cached explanation generator."""
    response = call_llm(
        prompt=prompt,
        temperature=0.2
    )
    return response.strip()

def generate_explanation(prompt: str) -> str:
    """
    Generate explanation with caching.
    Uses prompt hash to cache identical requests.
    """
    # Create hash of prompt for caching
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    
    try:
        return _cached_explanation(prompt_hash, prompt)
    except Exception as e:
        print(f"LLM call failed: {e}")
        return None