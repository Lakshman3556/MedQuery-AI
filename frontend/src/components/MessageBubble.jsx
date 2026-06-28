import React from "react";
import { User, Film } from "lucide-react";

export const MessageBubble = ({ message, onCitationClick }) => {
  const isUser = message.sender === "user";

  const renderMessageContent = (text, citations) => {
    if (isUser) return <p className="message-text">{text}</p>;

    const citationRegex = /(\[Source:\s*([^\]]+)\])/g;
    const parts = text.split(citationRegex);

    if (parts.length === 1) {
      return <p className="message-text">{text}</p>;
    }

    const elements = [];
    let idx = 0;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!part) continue;

      if (part.startsWith("[Source:")) {
        const filename = parts[i + 1];
        i++; // skip filename index

        const citationDetail = citations?.find(
          (c) => c.source_file.toLowerCase() === filename?.toLowerCase()
        );

        elements.push(
          <span
            key={`cite-${idx++}`}
            className="citation-badge"
            onClick={() => onCitationClick(citationDetail || { source_file: filename, text: "Cinema database details", collection: "N/A", similarity: 1.0 })}
          >
            [Source: {filename}]
          </span>
        );
      } else {
        elements.push(<span key={`text-${idx++}`}>{part}</span>);
      }
    }

    return <p className="message-text">{elements}</p>;
  };

  return (
    <div className={`message-wrapper ${isUser ? "user-msg" : "assistant-msg"}`}>
      <div className="message-avatar">
        {isUser ? <User size={18} /> : <Film size={18} />}
      </div>
      <div className="message-bubble-content">
        <div className="message-sender-name">
          {isUser ? "Cinephile" : "సినిma Assistant"}
        </div>
        {renderMessageContent(message.text, message.citations)}
      </div>
    </div>
  );
};
