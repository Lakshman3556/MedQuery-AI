import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from backend.services.retriever import retriever
from backend.services.rewriter import rewrite_query
from backend.services.memory import memory_manager
from backend.services.generator import generate_response_stream
from backend.guardrails.confidence import check_confidence

router = APIRouter()

class ChatRequest(BaseModel):
    question: str = Field(..., max_length=500, description="Natural language clinical question")
    session_id: str = Field(..., description="Unique session ID for conversation memory")

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    POST /chat endpoint that streams responses via Server-Sent Events (SSE).
    """
    question = request.question.strip()
    session_id = request.session_id.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID cannot be empty.")
        
    print(f"[CHAT] Received question: '{question}' for session: '{session_id}'")
    
    # 1. Load history from memory
    history_string = memory_manager.load_history_string(session_id)

    # 2. Rewrite the query
    rewritten_query = rewrite_query(question, history_string)
    print(f"[CHAT] Rewritten query: '{rewritten_query}'")
    
    # 3. Retrieve relevant context chunks
    context_chunks, avg_similarity = retriever.retrieve(rewritten_query)
    
    # 4. Perform confidence guardrail check
    refusal = check_confidence(avg_similarity)
    if refusal:
        print(f"[CHAT] Refusing query due to low confidence: {avg_similarity:.4f}")
        
        # We define an async generator to stream the refusal message via SSE
        async def refusal_generator():
            # Send the refusal answer token
            yield {
                "event": "message",
                "data": json.dumps({"token": refusal["answer"], "refused": True})
            }
            # Send empty citations
            yield {
                "event": "message",
                "data": json.dumps({"citations": []})
            }
            
        return EventSourceResponse(refusal_generator())
    
    # 5. Define generator for the actual LLM stream
    async def chat_stream_generator():
        accumulated_tokens = []
        try:
            # We wrap the original generate_response_stream
            async for sse_event in generate_response_stream(question, context_chunks, history_string):
                # Parse the incoming events back to dictionaries to yield them correctly via sse-starlette
                if sse_event.startswith("data: "):
                    data_str = sse_event[6:].strip()
                    try:
                        data_json = json.loads(data_str)
                        if "token" in data_json:
                            accumulated_tokens.append(data_json["token"])
                        yield {
                            "event": "message",
                            "data": data_str
                        }
                    except Exception:
                        yield {
                            "event": "message",
                            "data": data_str
                        }
        finally:
            # After stream finishes or is aborted, add the turn to session memory
            full_answer = "".join(accumulated_tokens).strip()
            if full_answer:
                memory_manager.add_turn(session_id, question, full_answer)
                print(f"[CHAT] Session '{session_id}' updated (finally). Total history size: {len(memory_manager.get_session_memory(session_id).chat_memory.messages) // 2} turns.")

    return EventSourceResponse(chat_stream_generator())
