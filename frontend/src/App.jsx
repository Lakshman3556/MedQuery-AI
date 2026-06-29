import React, { useState, useEffect } from "react";
import { ChatWindow } from "./components/ChatWindow";
import { CitationCard } from "./components/CitationCard";
import { useStream } from "./hooks/useStream";
import { ShieldAlert, Film, RefreshCw, Star, Sparkles, Video, Camera, Tv, Ticket, Clapperboard } from "lucide-react";

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
      {/* Cinematic Projector Beams */}
      <div className="projector-ray ray-left" />
      <div className="projector-ray ray-right" />

      {/* Floating Cinema Particles */}
      <div className="floating-background">
        <Film className="float-icon float-1" size={24} />
        <Ticket className="float-icon float-2" size={32} />
        <Clapperboard className="float-icon float-3" size={28} />
        <Star className="float-icon float-4" size={20} />
        <Sparkles className="float-icon float-5" size={22} />
        <Video className="float-icon float-6" size={30} />
        <Camera className="float-icon float-7" size={26} />
        <Tv className="float-icon float-8" size={24} />
        <Star className="float-icon float-9" size={18} />
        <Film className="float-icon float-10" size={26} />
      </div>

      <header className="app-header">
        <div className="header-brand">
          <Film className="brand-logo" size={24} />
          <h1 className="brand-name">సినిma AI</h1>
          <span className="brand-badge">Cinema RAG v1.1</span>
        </div>
        <button className="reset-session-btn" type="button" onClick={handleResetSession} title="Reset Conversation Session">
          <RefreshCw size={16} />
          <span>Reset Session</span>
        </button>
      </header>

      {/* Cinema Marquee / Now Playing Banner */}
      <div className="cinema-marquee-container">
        <div className="marquee-label">NOW PLAYING:</div>
        <div className="cinema-marquee">
          <div className="marquee-track">
            <span>🍿 Welcome to సినిమా AI! Ask about your favorite movies 🎬</span>
            <span>🔥 Ingested Chunks: 40,869 Cinema Plots fully indexed! 🚀</span>
            <span>🌟 Tollywood and Hollywood database loaded with Director and Cast metadata! 🎥</span>
            <span>🍿 Welcome to సినిమా AI! Ask about your favorite movies 🎬</span>
            <span>🔥 Ingested Chunks: 40,869 Cinema Plots fully indexed! 🚀</span>
            <span>🌟 Tollywood and Hollywood database loaded with Director and Cast metadata! 🎥</span>
          </div>
        </div>
      </div>

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
            Disclaimer: BROoooooooooooo nenu  RAG ni I have 40,869 cinemala context indexing fully loaded. If I hallucinate, please DHOBBAKANDI!
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
