import { useState, useCallback } from "react";

export const useStream = (backendUrl = "http://localhost:8000") => {
  const [loading, setLoading] = useState(false);

  const streamMessage = useCallback(
    async (question, sessionId, onToken, onCitations, onError) => {
      setLoading(true);
      try {
        const response = await fetch(`${backendUrl}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ question, session_id: sessionId }),
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last partial line in buffer
          buffer = lines.pop();

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data: ")) {
              const dataStr = trimmed.slice(6);
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.token !== undefined) {
                  onToken(parsed.token, parsed.refused || false);
                } else if (parsed.citations !== undefined) {
                  onCitations(parsed.citations);
                }
              } catch (e) {
                console.error("Failed to parse SSE event data:", dataStr, e);
              }
            }
          }
        }
      } catch (err) {
        console.error("Streaming error:", err);
        if (onError) onError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [backendUrl]
  );

  return { streamMessage, loading };
};
