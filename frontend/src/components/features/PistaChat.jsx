// frontend/src/components/features/PistaChat.jsx
import React, { useState, useEffect, useCallback } from "react";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";
import Marketplace from "./Marketplace";

// Common prompts that can be used as chips
const COMMON_PROMPTS = [
  "Games similar to",
  "Games different from",
  "Compare",
  "In my collection",
  "Different theme",
  "Same mechanics",
];

// Player count options for chips
const PLAYER_COUNTS = [1, 2, 3, 4, 5, 6, 7, 8];

function PistaChat({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [inputRef, setInputRef] = useState(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [chips, setChips] = useState([]);
  const [promptChips, setPromptChips] = useState([]);
  const [gameChips, setGameChips] = useState([]);
  const [playerChips, setPlayerChips] = useState([]);
  const [useCollection, setUseCollection] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [gameSearchQuery, setGameSearchQuery] = useState("");
  const [gameSearchResults, setGameSearchResults] = useState([]);
  const [showGameSearch, setShowGameSearch] = useState(false);
  const [gameSearchEnabled, setGameSearchEnabled] = useState(false);
  const [marketplaceGame, setMarketplaceGame] = useState(null);

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

  // Insert text at cursor position
  const insertTextAtCursor = (text) => {
    if (!inputRef) return;
    const start = inputRef.selectionStart || cursorPosition;
    const end = inputRef.selectionEnd || cursorPosition;
    const newText = input.slice(0, start) + text + input.slice(end);
    setInput(newText);
    // Set cursor position after inserted text
    setTimeout(() => {
      if (inputRef) {
        const newPos = start + text.length;
        inputRef.setSelectionRange(newPos, newPos);
        setCursorPosition(newPos);
      }
    }, 0);
  };

  const selectGame = (game) => {
    // Add game to chips if not already present
    if (!gameChips.find(g => g.id === game.id)) {
      setGameChips([...gameChips, game]);
    }
    setGameSearchQuery("");
    setGameSearchResults([]);
    setShowGameSearch(false);
    // Insert game name at cursor position
    insertTextAtCursor(game.name + " ");
  };

  const removeGameChip = (gameId) => {
    setGameChips(gameChips.filter(g => g.id !== gameId));
    // Remove game name from input if present
    const game = gameChips.find(g => g.id === gameId);
    if (game) {
      const regex = new RegExp(`\\b${game.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
      setInput(input.replace(regex, '').replace(/\s+/g, ' ').trim());
    }
  };

  const addPromptChip = (prompt) => {
    if (!promptChips.includes(prompt)) {
      setPromptChips([...promptChips, prompt]);
      insertTextAtCursor(prompt + " ");
    }
  };

  const removePromptChip = (prompt) => {
    setPromptChips(promptChips.filter(p => p !== prompt));
    // Remove prompt from input if present
    const regex = new RegExp(`\\b${prompt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    setInput(input.replace(regex, '').replace(/\s+/g, ' ').trim());
  };

  const addPlayerChip = (playerCount) => {
    if (!playerChips.includes(playerCount)) {
      setPlayerChips([...playerChips, playerCount]);
      insertTextAtCursor(`${playerCount} players `);
    }
  };

  const removePlayerChip = (playerCount) => {
    setPlayerChips(playerChips.filter(p => p !== playerCount));
    // Remove player count from input if present
    const regex = new RegExp(`\\b${playerCount}\\s*players?\\b`, 'gi');
    setInput(input.replace(regex, '').replace(/\s+/g, ' ').trim());
  };

  const handleGameChipClick = (game) => {
    // Add game name to input at cursor position
    insertTextAtCursor(game.name + " ");
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
    setPromptChips([]);
    setGameChips([]);
    setPlayerChips([]);
    setUseCollection(false);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);

    const context = {
      last_game_id: gameChips.length > 0 ? gameChips[0].id : null,
      useCollection: useCollection,
      selected_game_id: gameChips.length > 0 ? gameChips[0].id : null,
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
          selected_game_id: gameChips.length > 0 ? gameChips[0].id : null,
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
      // Keep game chips for next query in the thread (don't clear them)
      // setGameChips([]); // Removed - persist chips across messages
      // Keep prompt chips and player chips too for context
      // setPromptChips([]); // Keep for context
      // setPlayerChips([]); // Keep for context
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
      {marketplaceGame && (
        <Marketplace
          gameId={marketplaceGame.id}
          gameName={marketplaceGame.name}
          onClose={() => setMarketplaceGame(null)}
        />
      )}
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
          <MessageList 
            messages={messages} 
            onGameClick={(game) => setMarketplaceGame({ id: game.game_id, name: game.name })}
          />
        </div>

        <div className="filter-bar">
          {chips.map((chip) => (
            <div className="chip" key={chip.facet}>
              {chip.facet}
            </div>
          ))}
          {promptChips.map((prompt) => (
            <div className="chip prompt-chip" key={prompt}>
              {prompt}
              <button
                onClick={() => removePromptChip(prompt)}
                className="chip-remove"
                title="Remove prompt"
              >
                ×
              </button>
            </div>
          ))}
          {gameChips.map((game) => (
            <div className="chip game-chip" key={game.id}>
              <span 
                onClick={() => handleGameChipClick(game)}
                style={{ cursor: "pointer", flex: 1 }}
                title="Click to add to input"
              >
                🎮 {game.name}
              </span>
              <button
                onClick={() => removeGameChip(game.id)}
                className="chip-remove"
                title="Remove game"
              >
                ×
              </button>
            </div>
          ))}
          {playerChips.map((playerCount) => (
            <div className="chip player-chip" key={playerCount}>
              👥 {playerCount} players
              <button
                onClick={() => removePlayerChip(playerCount)}
                className="chip-remove"
                title="Remove player count"
              >
                ×
              </button>
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
                    setShowGameSearch(false);
                  }
                }}
              />
              🔍 Game Search
            </label>
          </div>
          <div className="common-prompts">
            {COMMON_PROMPTS.filter(p => !promptChips.includes(p)).map((prompt) => (
              <button
                key={prompt}
                className="chip prompt-button"
                onClick={() => addPromptChip(prompt)}
                title="Add prompt"
              >
                + {prompt}
              </button>
            ))}
          </div>
          <div className="player-counts">
            {PLAYER_COUNTS.filter(p => !playerChips.includes(p)).map((count) => (
              <button
                key={count}
                className="chip player-button"
                onClick={() => addPlayerChip(count)}
                title="Add player count"
              >
                + {count} players
              </button>
            ))}
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
          <div className="chat-input-row">
            {/* Display context chips above input */}
            {(gameChips.length > 0 || promptChips.length > 0 || playerChips.length > 0) && (
              <div className="context-chips-display" style={{ marginBottom: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {gameChips.map((game) => (
                  <div className="chip game-chip" key={game.id}>
                    <span 
                      onClick={() => handleGameChipClick(game)}
                      style={{ cursor: "pointer", flex: 1 }}
                      title="Click to add to input"
                    >
                      🎮 {game.name}
                    </span>
                    <button
                      onClick={() => removeGameChip(game.id)}
                      className="chip-remove"
                      title="Remove game"
                    >
                      ×
                    </button>
                  </div>
                ))}
                {promptChips.map((prompt) => (
                  <div className="chip prompt-chip" key={prompt}>
                    {prompt}
                    <button
                      onClick={() => removePromptChip(prompt)}
                      className="chip-remove"
                      title="Remove prompt"
                    >
                      ×
                    </button>
                  </div>
                ))}
                {playerChips.map((playerCount) => (
                  <div className="chip player-chip" key={playerCount}>
                    👥 {playerCount} players
                    <button
                      onClick={() => removePlayerChip(playerCount)}
                      className="chip-remove"
                      title="Remove player count"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
            <input
              ref={setInputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setCursorPosition(e.target.selectionStart || 0);
              }}
              onSelect={(e) => {
                setCursorPosition(e.target.selectionStart || 0);
              }}
              onClick={(e) => {
                setCursorPosition(e.target.selectionStart || 0);
              }}
              onKeyUp={(e) => {
                setCursorPosition(e.target.selectionStart || 0);
              }}
              placeholder={gameChips.length > 0 ? `Ask about games similar to ${gameChips[0].name}...` : "Ask: 'Games in my collection closest to Brass: Birmingham but different theme'"}
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

function MessageList({ messages, onGameClick }) {
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
              <GameResultList 
                results={m.results} 
                onGameClick={onGameClick}
              />
            )}
          </div>
        ))
      )}
    </div>
  );
}

function GameResultList({ results, onGameClick }) {
  return (
    <div className="game-results">
      {results.map((r) => (
        <div 
          className="game-card" 
          key={r.game_id}
          onClick={() => onGameClick && onGameClick(r)}
          style={{ cursor: onGameClick ? "pointer" : "default" }}
        >
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
                    : (r.embedding_similarity !== undefined ? r.embedding_similarity.toFixed(2) : "N/A")}
                </span>
                {r.average_rating && (
                  <span style={{ marginLeft: "1rem" }}>
                    ⭐ {r.average_rating.toFixed(1)}
                    {r.num_ratings && (
                      <span style={{ marginLeft: "0.5rem", opacity: 0.7, fontSize: "0.9em" }}>
                        ({r.num_ratings.toLocaleString()})
                      </span>
                    )}
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
