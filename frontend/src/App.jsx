import React, { useState, useEffect } from "react";
import { ChatWindow } from "./components/ChatWindow";
import { CitationCard } from "./components/CitationCard";
import { useStream } from "./hooks/useStream";
import { ShieldAlert, Film, RefreshCw } from "lucide-react";

const generateUUID = () => {
  return "session-" + Math.random().toString(36).substr(2, 9) + "-" + Date.now().toString(36);
};

function App() {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState([]);
  const [currentStreamingText, setCurrentStreamingText] = useState("");
  const [activeCitation, setActiveCitation] = useState(null);
  const { streamMessage, loading } = useStream("http://localhost:8000");

  useEffect(() => {
    setSessionId(generateUUID());
  }, []);

  const handleSendMessage = async (text) => {
    const userMsg = { sender: "user", text };
    setMessages((prev) => [...prev, userMsg]);

    let fullStreamingAnswer = "";
    let finalCitations = [];

    await streamMessage(
      text,
      sessionId,
      (token, refused) => {
        fullStreamingAnswer += token;
        setCurrentStreamingText(fullStreamingAnswer);
      },
      (citations) => {
        finalCitations = citations;
      },
      (error) => {
        console.error("Chat streaming failed:", error);
        const errorMsg = {
          sender: "assistant",
          text: `An error occurred: ${error}. Make sure the backend server is running on http://localhost:8000 and your LLM API keys are valid.`,
          citations: [],
        };
        setMessages((prev) => [...prev, errorMsg]);
        setCurrentStreamingText("");
      }
    );

    if (fullStreamingAnswer) {
      const assistantMsg = {
        sender: "assistant",
        text: fullStreamingAnswer,
        citations: finalCitations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setCurrentStreamingText("");
    }
  };

  const handleResetSession = () => {
    setMessages([]);
    setCurrentStreamingText("");
    setSessionId(generateUUID());
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-brand">
          <Film className="brand-logo" size={24} />
          <h1 className="brand-name">సినిma AI</h1>
          <span className="brand-badge">RAG Assistant</span>
        </div>
        <button className="reset-session-btn" type="button" onClick={handleResetSession} title="Reset Conversation Session">
          <RefreshCw size={16} />
          <span>Reset Session</span>
        </button>
      </header>

      <main className="app-main">
        <div className="main-content-layout">
          <ChatWindow
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={loading}
            currentStreamingText={currentStreamingText}
            onCitationClick={setActiveCitation}
          />
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-disclaimer">
          <ShieldAlert size={14} className="disclaimer-icon" />
          <span>
            Disclaimer: సినిma AI is an educational RAG prototype for English and తెలుగు movies. It should not be used for actual clinical advice.
          </span>
        </div>
      </footer>

      {activeCitation && (
        <CitationCard citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}
    </div>
  );
}

export default App;
