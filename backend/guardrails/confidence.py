from typing import Dict, Any

def check_confidence(avg_similarity: float, threshold: float = 0.45) -> Dict[str, Any]:
    """
    Checks if the average similarity score of the retrieved chunks is below the safety threshold.
    If below threshold, returns a standardized refusal payload.
    """
    if avg_similarity < threshold:
        return {
            "answer": "I could not find reliable information on this in my cinema database.",
            "citations": [],
            "refused": True
        }
    return {}
