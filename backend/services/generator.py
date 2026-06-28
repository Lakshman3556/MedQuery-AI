import os
import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any
from backend import config

# Configure the corresponding async API client
if config.LLM_PROVIDER == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
elif config.LLM_PROVIDER == "groq":
    from groq import AsyncGroq
    groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)

async def generate_response_stream(
    question: str, 
    context_chunks: List[Dict[str, Any]], 
    history_string: str
) -> AsyncGenerator[str, None]:
    """
    Assembles context, history, and question, calls the LLM stream,
    and yields SSE events containing tokens and final citations.
    """
       # 1. Format the context block
    formatted_chunks = []
    citations = []
    for i, chunk in enumerate(context_chunks):
        meta = chunk["metadata"]
        # Format citation reference as "Movie Name (Year)" instead of the raw CSV filename
        citation_ref = f"{meta.get('movie_name')} ({meta.get('year')})"
        col = chunk.get("collection", "unknown")
        text = chunk["text"]
        formatted_chunks.append(f"Chunk {i+1} [Source: {citation_ref}, Collection: {col}]:\n{text}\n")
        citations.append({
            "id": chunk["id"],
            "source_file": citation_ref,
            "collection": col,
            "text": text,
            "similarity": chunk.get("similarity", 0.0)
        })
        
    context_block = "\n".join(formatted_chunks) if formatted_chunks else "No relevant context found."

    # 2. Setup prompt variables
    from backend.prompts.templates import SYSTEM_PROMPT, USER_TEMPLATE
    user_prompt = USER_TEMPLATE.format(
        history=history_string if history_string.strip() else "No previous turns.",
        context=context_block,
        question=question
    )
    
    try:
        if config.LLM_PROVIDER == "gemini":
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT
            )
            response = await model.generate_content_async(
                contents=user_prompt,
                generation_config={"max_output_tokens": 600, "temperature": 0.0},
                stream=True
            )
            async for chunk in response:
                token = chunk.text
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    await asyncio.sleep(0.01) # Yield control
                    
        elif config.LLM_PROVIDER == "groq":
            stream = await groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=600,
                temperature=0.7,
                stream=True
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    
        # 3. Yield the final citations JSON block
        yield f"data: {json.dumps({'citations': citations})}\n\n"
        
    except Exception as e:
        print(f"[GENERATOR] Error streaming response: {e}")
        error_msg = "An error occurred while generating the answer. Please try again."
        yield f"data: {json.dumps({'token': error_msg})}\n\n"
        yield f"data: {json.dumps({'citations': []})}\n\n"
