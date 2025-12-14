// frontend/src/components/PistaChat.jsx
import React, { useState, useEffect, useCallback } from "react";
import { authService } from "../auth";

const API_BASE = "http://localhost:8000";

function PistaChat({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [chips, setChips] = useState([]);
  const [useCollection, setUseCollection] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [gameSearchQuery, setGameSearchQuery] = useState("");
  const [gameSearchResults, setGameSearchResults] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [showGameSearch, setShowGameSearch] = useState(false);
  const [gameSearchEnabled, setGameSearchEnabled] = useState(false);

  const loadChatHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/chat/history`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setChatHistory(data);
      }
    } catch (err) {
      console.error("Failed to load chat history:", err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadChatHistory();
    }
  }, [loadChatHistory, user]);

  const handleGameSearch = async (query) => {
    setGameSearchQuery(query);
    if (query.length < 2) {
      setGameSearchResults([]);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/games/search?q=${encodeURIComponent(query)}&limit=5`);
      if (res.ok) {
        const data = await res.json();
        setGameSearchResults(data);
        setShowGameSearch(true);
      }
    } catch (err) {
      console.error("Game search failed:", err);
    }
  };

  const selectGame = (game) => {
    setSelectedGame(game);
    setGameSearchQuery("");
    setGameSearchResults([]);
    setShowGameSearch(false);
    // Add game name to input text
    if (input.trim()) {
      setInput(input + " " + game.name);
    } else {
      setInput(game.name);
    }
  };

  const loadThread = async (threadIdToLoad) => {
    try {
      const res = await fetch(`${API_BASE}/chat/history/${threadIdToLoad}`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const threadMessages = await res.json();
        const formattedMessages = threadMessages.map((msg) => ({
          role: msg.role,
          text: msg.message,
          results: msg.metadata?.results || [],
          querySpec: msg.metadata?.query_spec || {},
        }));
        setMessages(formattedMessages);
        setThreadId(threadIdToLoad);
      }
    } catch (err) {
      console.error("Failed to load thread:", err);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setThreadId(null);
    setChips([]);
    setUseCollection(false);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);

    const context = {
      last_game_id: null,
      useCollection,
    };
    
    // If useCollection is checked, explicitly set scope in message
    let messageText = input;
    if (useCollection && !messageText.toLowerCase().includes("in my collection") && !messageText.toLowerCase().includes("my collection")) {
      messageText = messageText + " in my collection";
    }

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user?.id?.toString() || null,
          message: messageText,
          context,
          thread_id: threadId,
          selected_game_id: selectedGame?.id || null,
        }),
      });

      const data = await res.json();

      const botMsg = {
        role: "assistant",
        text: data.reply_text,
        results: data.results || [],
        querySpec: data.query_spec || {},
      };

      setMessages((prev) => [...prev, botMsg]);
      setInput("");
      setSelectedGame(null);
      setGameSearchQuery("");

      // Update thread ID if this was a new thread
      if (data.thread_id && !threadId && user) {
        setThreadId(data.thread_id);
        await loadChatHistory(); // Refresh history list
      }

      // Update chips based on constraints
      const constraints = data.query_spec?.constraints || {};
      const newChips = Object.entries(constraints).map(([facet, rule]) => ({
        facet,
        rule,
      }));
      setChips(newChips);

      // Update "in my collection" toggle from scope if you like
      if (data.query_spec?.scope === "user_collection") {
        setUseCollection(true);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      alert("Failed to send message. Please try again.");
    }
  };

  return (
    <div className="pista-chat-container">
      {user && (
        <div className={`chat-history-sidebar ${showHistory ? "visible" : ""}`}>
          <div className="history-header">
            <h3>Chat History</h3>
            <button onClick={startNewChat} className="new-chat-button">
              New Chat
            </button>
          </div>
          {loadingHistory ? (
            <div className="loading">Loading...</div>
          ) : (
            <div className="history-list">
              {chatHistory.map((thread) => (
                <div
                  key={thread.id}
                  className={`history-item ${thread.id === threadId ? "active" : ""}`}
                  onClick={() => loadThread(thread.id)}
                >
                  <div className="history-title">{thread.title}</div>
                  <div className="history-date">
                    {new Date(thread.updated_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="pista-chat">
        {user && (
          <div className="chat-header">
            <button
              className="toggle-history"
              onClick={() => setShowHistory(!showHistory)}
            >
              {showHistory ? "◀" : "▶"} History
            </button>
          </div>
        )}
        <div className="chat-window">
          <MessageList messages={messages} />
        </div>

        <div className="filter-bar">
          {chips.map((chip) => (
            <div className="chip" key={chip.facet}>
              {chip.facet}
            </div>
          ))}
          <div className="chip toggle">
            <label>
              <input
                type="checkbox"
                checked={useCollection}
                onChange={(e) => setUseCollection(e.target.checked)}
              />
              In my collection
            </label>
          </div>
          <div className="chip toggle">
            <label>
              <input
                type="checkbox"
                checked={gameSearchEnabled}
                onChange={(e) => {
                  setGameSearchEnabled(e.target.checked);
                  if (!e.target.checked) {
                    setGameSearchQuery("");
                    setGameSearchResults([]);
                    setSelectedGame(null);
                    setShowGameSearch(false);
                  }
                }}
              />
              🔍 Game Search
            </label>
          </div>
        </div>

        <div className="chat-input-container">
          {gameSearchEnabled && (
            <div className="game-search-container">
              <input
                type="text"
                placeholder="Search for a game to add to context..."
                value={gameSearchQuery}
                onChange={(e) => handleGameSearch(e.target.value)}
                onFocus={() => gameSearchQuery.length >= 2 && setShowGameSearch(true)}
                className="game-search-input"
              />
              {showGameSearch && gameSearchResults.length > 0 && (
                <div className="game-search-dropdown">
                  {gameSearchResults.map((game) => (
                    <div
                      key={game.id}
                      className="game-search-item"
                      onClick={() => selectGame(game)}
                    >
                      {game.name}
                      {game.year_published && ` (${game.year_published})`}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {selectedGame && (
            <div className="selected-game-chip" style={{ marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span>🎮 {selectedGame.name}</span>
              <button 
                onClick={() => {
                  setSelectedGame(null);
                  // Remove game name from input if it's there
                  if (input.includes(selectedGame.name)) {
                    setInput(input.replace(selectedGame.name, "").trim());
                  }
                }} 
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2em" }}
              >
                ×
              </button>
            </div>
          )}
          <div className="chat-input-row">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={selectedGame ? `Ask about games similar to ${selectedGame.name}...` : "Ask: 'Games in my collection closest to Brass: Birmingham but different theme'"}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />
            <button onClick={sendMessage}>Send</button>
          </div>
          <div className="image-upload-section">
            <input
              type="file"
              accept="image/*"
              id="image-upload"
              style={{ display: "none" }}
              onChange={async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append("file", file);
                
                try {
                  const res = await fetch(`${API_BASE}/image/generate`, {
                    method: "POST",
                    headers: authService.getAuthHeaders(),
                    body: formData,
                  });
                  
                  if (res.ok) {
                    const data = await res.json();
                    const imageMsg = {
                      role: "assistant",
                      text: `Generated image from your upload. Prompt: ${data.prompt}`,
                      image: data.image,
                    };
                    setMessages((prev) => [...prev, imageMsg]);
                  } else {
                    alert("Failed to process image");
                  }
                } catch (err) {
                  console.error("Image upload failed:", err);
                  alert("Failed to upload image");
                }
              }}
            />
            <label htmlFor="image-upload" className="image-upload-button">
              📷 Upload Image
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageList({ messages }) {
  const highlightText = (text, querySpec) => {
    if (!querySpec || !text) return text;
    
    const intent = querySpec.intent || "";
    const constraints = querySpec.constraints || {};
    const isDissimilarity = intent.includes("different") || 
                           Object.keys(constraints).some(k => 
                             constraints[k].jaccard_max !== undefined || 
                             constraints[k].max_overlap !== undefined
                           );
    const isSimilarity = intent.includes("similar") || 
                        intent.includes("compare") ||
                        Object.keys(constraints).some(k => 
                          constraints[k].jaccard_min !== undefined || 
                          constraints[k].min_overlap !== undefined
                        );
    
    // Split text into sentences and highlight relevant parts
    const sentences = text.split(/([.!?]\s+)/);
    return sentences.map((sentence, i) => {
      if (isDissimilarity && (sentence.toLowerCase().includes("different") || 
                               sentence.toLowerCase().includes("dissimilar") ||
                               sentence.toLowerCase().includes("not"))) {
        return <span key={i} className="highlight-different">{sentence}</span>;
      }
      if (isSimilarity && (sentence.toLowerCase().includes("similar") || 
                           sentence.toLowerCase().includes("same") ||
                           sentence.toLowerCase().includes("compare") ||
                           sentence.toLowerCase().includes("overlap"))) {
        return <span key={i} className="highlight-similar">{sentence}</span>;
      }
      return sentence;
    });
  };
  
  return (
    <div className="messages">
      {messages.length === 0 ? (
        <div className="empty-chat">Start a conversation to see messages here</div>
      ) : (
        messages.map((m, idx) => (
          <div key={idx} className={`msg msg--${m.role}`}>
            <div className="msg-text">
              {m.role === "assistant" && m.querySpec 
                ? highlightText(m.text, m.querySpec)
                : m.text}
            </div>
            {m.image && (
              <img src={m.image} alt="Generated" className="generated-image" />
            )}
            {m.results && m.results.length > 0 && (
              <GameResultList results={m.results} />
            )}
          </div>
        ))
      )}
    </div>
  );
}

function GameResultList({ results }) {
  return (
    <div className="game-results">
      {results.map((r) => (
        <div className="game-card" key={r.game_id}>
          <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
            {r.thumbnail && (
              <img 
                src={r.thumbnail} 
                alt={r.name}
                style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "4px" }}
              />
            )}
            <div style={{ flex: 1 }}>
              <div className="game-card__title">{r.name}</div>
              {r.reason_summary && (
                <div className="game-card__reason">{r.reason_summary}</div>
              )}
              <div className="game-card__meta">
                <span>
                  Similarity:{" "}
                  {r.final_score !== undefined
                    ? r.final_score.toFixed(2)
                    : r.embedding_similarity.toFixed(2)}
                </span>
                {r.average_rating && (
                  <span style={{ marginLeft: "1rem" }}>
                    ⭐ {r.average_rating.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default PistaChat;
