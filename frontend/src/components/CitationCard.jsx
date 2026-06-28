import React from "react";
import { X, BookOpen, Tag, Clipboard } from "lucide-react";

export const CitationCard = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div className="citation-overlay" onClick={onClose}>
      <div className="citation-modal" onClick={(e) => e.stopPropagation()}>
        <div className="citation-header">
          <div className="citation-title-wrapper">
            <BookOpen className="citation-icon" size={18} />
            <h3 className="citation-title">{citation.source_file}</h3>
          </div>
          <button className="citation-close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="citation-body">
          <div className="citation-meta">
            <div className="meta-badge">
              <Tag size={12} className="badge-icon" />
              <span>Collection: {citation.collection}</span>
            </div>
            <div className="meta-badge">
              <Clipboard size={12} className="badge-icon" />
              <span>Similarity: {(citation.similarity * 100).toFixed(1)}%</span>
            </div>
          </div>
          <p className="citation-text">"{citation.text}"</p>
        </div>
      </div>
    </div>
  );
};
