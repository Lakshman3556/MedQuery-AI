import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Film } from "lucide-react";
import { MessageBubble } from "./MessageBubble";

// Import local meme images
import absCMeme from "../assets/memes/abs_C.jpg";
import rajMeme from "../assets/memes/raj.jpg";

const MemeImage = ({ src, alt, fallbackGradient }) => {
  const [hasError, setHasError] = useState(false);

  if (hasError || !src) {
    return <div className={`suggestion-card-bg ${fallbackGradient}`} />;
  }

  return (
    <img
      src={src}
      alt={alt}
      className="meme-suggestion-img"
      onError={() => setHasError(true)}
    />
  );
};

export const ChatWindow = ({ messages, onSendMessage, loading, currentStreamingText, onCitationClick }) => {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage(input.trim());
    setInput("");
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStreamingText]);

  // Two suggestion buttons using raw local meme assets
  const suggestions = [
    {
      title: "English Movies",
      query: "Explain the rules of dream levels and time dilation in Inception.",
      meme: absCMeme,
      gradient: "grad-blue"
    },
    {
      title: "తెలుగు Movies",
      query: "Why did Kattappa kill Baahubali and what is the reason behind it?",
      meme: rajMeme,
      gradient: "grad-red"
    }
  ];

  return (
    <div className="chat-window-container">
      <div className="messages-scroll-area">
        {messages.length === 0 ? (
          <div className="welcome-hero">
            <h2 className="welcome-title">సినిma AI</h2>
            <p className="welcome-subtitle">
              Interactive Q&A Search Engine for English and తెలుగు Movies.
            </p>

            <div className="suggestions-grid suggestions-two-cards">
              {suggestions.map((s, idx) => (
                <div
                  key={idx}
                  className="meme-suggestion-btn"
                >
                  <MemeImage src={s.meme} alt={s.title} fallbackGradient={s.gradient} />
                </div>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} onCitationClick={onCitationClick} />
          ))
        )}

        {currentStreamingText && (
          <div className="message-wrapper assistant-msg streaming">
            <div className="message-avatar">
              <Film size={18} />
            </div>
            <div className="message-bubble-content">
              <div className="message-sender-name">సినిma Assistant</div>
              <p className="message-text">{currentStreamingText}</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about movie plots, cast details, or fun trivia..."
          disabled={loading}
        />
        <button type="submit" className="chat-send-btn" disabled={!input.trim() || loading}>
          {loading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
        </button>
      </form>
    </div>
  );
};
