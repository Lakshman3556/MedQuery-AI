import os
from backend import config

# Configure the corresponding API client based on config
if config.LLM_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
elif config.LLM_PROVIDER == "groq":
    from groq import Groq
    groq_client = Groq(api_key=config.GROQ_API_KEY)

def rewrite_query(query: str, history_string: str = "") -> str:
    """
    Rewrites vague or complex user queries to optimize them for vector database search.
    If history is provided, resolves pronouns (e.g. "it", "he", "she", "that movie")
    based on the conversation history to make the query standalone.
    If LLM rewrite fails, it falls back to returning the original query.
    """
    if not query.strip():
        return query
        
    if history_string.strip():
        prompt = f"""Given the following conversation history and a follow-up query, rewrite the follow-up query to be a standalone, clear, and complete search query optimized for a vector database search.
Resolve any pronouns, conversational shortcuts, or implicit references (like "it", "that movie", "the director", "cast") using the context of the history.
If the query is already standalone and does not reference previous turns, just clean it up for search.
Return ONLY the rewritten search query and nothing else. Do not add quotes.

CONVERSATION HISTORY:
{history_string}

FOLLOW-UP QUERY: {query}

Standalone search query:"""
    else:
        prompt = f"Rewrite this movie/cinema search query for clarity and optimal semantic search retrieval. Return ONLY the rewritten query text and nothing else: {query}"

    try:
        if config.LLM_PROVIDER == "gemini":
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            rewritten = response.text.strip()
            return rewritten if rewritten else query
            
        elif config.LLM_PROVIDER == "groq":
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=100,
                temperature=0.0
            )
            rewritten = chat_completion.choices[0].message.content.strip()
            
            # Strip quotes if the model wrapped the response
            if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
                rewritten = rewritten[1:-1].strip()
            return rewritten if rewritten else query
            
    except Exception as e:
        print(f"[REWRITER] Error rewriting query: {e}. Falling back to original.")
        return query
