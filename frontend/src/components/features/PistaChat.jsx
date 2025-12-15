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

// Playtime options for chips (in minutes)
const PLAYTIME_OPTIONS = [
  { label: "15 min", value: 15 },
  { label: "30 min", value: 30 },
  { label: "45 min", value: 45 },
  { label: "1 hour", value: 60 },
  { label: "1.5 hours", value: 90 },
  { label: "2 hours", value: 120 },
  { label: "3+ hours", value: 180 },
];

function PistaChat({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [inputRef, setInputRef] = useState(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [chips, setChips] = useState([]);
  const [promptChips, setPromptChips] = useState([]);
  const [gameChips, setGameChips] = useState([]);
  const [playerChips, setPlayerChips] = useState([]);
  const [playtimeChips, setPlaytimeChips] = useState([]);
  const [useCollection, setUseCollection] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [gameSearchResults, setGameSearchResults] = useState([]);
  const [showGameSearch, setShowGameSearch] = useState(false);
  const [atMentionActive, setAtMentionActive] = useState(false);
  const [atMentionPosition, setAtMentionPosition] = useState(0);
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
    if (query.length < 2) {
      setGameSearchResults([]);
      setShowGameSearch(false);
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

  // Handle @ mention in input
  const handleInputChange = (e) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart || 0;
    setInput(value);
    setCursorPosition(cursorPos);

    // Check for @ mention
    const textBeforeCursor = value.substring(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    if (lastAtIndex !== -1) {
      // Check if @ is not part of an email or already completed mention
      const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);
      // Check if there's a space or newline after @ (mention completed)
      const hasSpaceAfterAt = textAfterAt.includes(' ') || textAfterAt.includes('\n');
      // Simple check: if @ is followed by alphanumeric and no space, it's an active mention
      const isActiveMention = /^[a-zA-Z0-9]*$/.test(textAfterAt) && !hasSpaceAfterAt;
      
      if (isActiveMention) {
        // @ mention is active
        const query = textAfterAt;
        setAtMentionActive(true);
        setAtMentionPosition(lastAtIndex);
        if (query.length >= 2) {
          handleGameSearch(query);
        } else {
          setShowGameSearch(false);
          setGameSearchResults([]);
        }
      } else {
        setAtMentionActive(false);
        setShowGameSearch(false);
        setGameSearchResults([]);
      }
    } else {
      setAtMentionActive(false);
      setShowGameSearch(false);
      setGameSearchResults([]);
    }
  };

  const handleGameSelectFromMention = (game) => {
    if (!inputRef) return;
    
    // Find the @ position and query text
    const currentInput = input;
    const textBeforeAt = currentInput.substring(0, atMentionPosition);
    // Find where the query ends (space, end of string, or cursor position)
    const textAfterAt = currentInput.substring(atMentionPosition + 1);
    const queryEndMatch = textAfterAt.match(/^[^\s]*/);
    const queryEnd = queryEndMatch ? queryEndMatch[0].length : 0;
    const textAfterQuery = currentInput.substring(atMentionPosition + 1 + queryEnd);
    
    // Replace @query with game name
    const newText = textBeforeAt + game.name + " " + textAfterQuery;
    setInput(newText);
    
    // Add game to chips if not already present
    if (!gameChips.find(g => g.id === game.id)) {
      setGameChips([...gameChips, game]);
    }
    
    // Reset mention state
    setAtMentionActive(false);
    setShowGameSearch(false);
    setGameSearchResults([]);
    
    // Set cursor position after inserted game name
    setTimeout(() => {
      if (inputRef) {
        const newPos = textBeforeAt.length + game.name.length + 1;
        inputRef.setSelectionRange(newPos, newPos);
        setCursorPosition(newPos);
        inputRef.focus();
      }
    }, 0);
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
    if (atMentionActive) {
      handleGameSelectFromMention(game);
    } else {
      // Add game to chips if not already present
      if (!gameChips.find(g => g.id === game.id)) {
        setGameChips([...gameChips, game]);
      }
      setGameSearchResults([]);
      setShowGameSearch(false);
      // Insert game name at cursor position
      insertTextAtCursor(game.name + " ");
    }
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

  const addPlaytimeChip = (playtime) => {
    if (!playtimeChips.find(p => p.value === playtime.value)) {
      setPlaytimeChips([...playtimeChips, playtime]);
      insertTextAtCursor(`${playtime.label} `);
    }
  };

  const removePlaytimeChip = (playtimeValue) => {
    const playtime = playtimeChips.find(p => p.value === playtimeValue);
    if (playtime) {
      setPlaytimeChips(playtimeChips.filter(p => p.value !== playtimeValue));
      // Remove playtime from input if present
      const regex = new RegExp(`\\b${playtime.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
      setInput(input.replace(regex, '').replace(/\s+/g, ' ').trim());
    }
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
    setPlaytimeChips([]);
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
      player_chips: playerChips,
      playtime_chips: playtimeChips.map(c => c.value),
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

      if (!res.ok) {
        let errorMessage = "Failed to send message";
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          errorMessage = `Server error: ${res.status} ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }

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
      alert(err.message || "Failed to send message. Please try again.");
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
            {playerChips.length === 0 && PLAYER_COUNTS.map((count) => (
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
          <div className="playtime-options">
            {playtimeChips.length === 0 && PLAYTIME_OPTIONS.map((playtime) => (
              <button
                key={playtime.value}
                className="chip playtime-button"
                onClick={() => addPlaytimeChip(playtime)}
                title="Add playtime"
              >
                + {playtime.label}
              </button>
            ))}
          </div>
        </div>

        <div className="chat-input-container" style={{ position: "relative" }}>
          {/* Game search dropdown for @ mentions */}
          {atMentionActive && showGameSearch && gameSearchResults.length > 0 && (
            <div className="game-search-dropdown" style={{ position: "absolute", bottom: "100%", left: 0, right: 0, marginBottom: "0.5rem", zIndex: 1000 }}>
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
          <div className="chat-input-row">
            {/* Display context chips above input */}
            {(gameChips.length > 0 || promptChips.length > 0 || playerChips.length > 0 || playtimeChips.length > 0) && (
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
                {playtimeChips.map((playtime) => (
                  <div className="chip playtime-chip" key={playtime.value}>
                    ⏱️ {playtime.label}
                    <button
                      onClick={() => removePlaytimeChip(playtime.value)}
                      className="chip-remove"
                      title="Remove playtime"
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
              onChange={handleInputChange}
              onSelect={(e) => {
                setCursorPosition(e.target.selectionStart || 0);
              }}
              onClick={(e) => {
                setCursorPosition(e.target.selectionStart || 0);
              }}
              onKeyUp={(e) => {
                setCursorPosition(e.target.selectionStart || 0);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !atMentionActive) {
                  sendMessage();
                } else if (e.key === "Escape") {
                  setAtMentionActive(false);
                  setShowGameSearch(false);
                }
              }}
              placeholder={gameChips.length > 0 ? `Ask about games similar to ${gameChips[0].name}...` : "Type @ to search for games, or ask: 'Games in my collection closest to Brass: Birmingham but different theme'"}
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
  if (!results || results.length === 0) {
    return null;
  }
  
  return (
    <div className="game-results">
      {results
        .filter(r => r && r.game_id) // Filter out invalid results
        .map((r) => (
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
                alt={r.name || "Game"}
                style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "4px" }}
              />
            )}
            <div style={{ flex: 1 }}>
              <div className="game-card__title">{r.name || `Game ${r.game_id}`}</div>
              {r.reason_summary && (
                <div className="game-card__reason">{r.reason_summary}</div>
              )}
              <div className="game-card__meta">
                <span>
                  Similarity:{" "}
                  {r.final_score !== undefined && r.final_score !== null
                    ? r.final_score.toFixed(2)
                    : (r.embedding_similarity !== undefined && r.embedding_similarity !== null
                        ? r.embedding_similarity.toFixed(2)
                        : "N/A")}
                </span>
                {r.average_rating && (
                  <span style={{ marginLeft: "1rem" }}>
                    ⭐ {typeof r.average_rating === 'number' ? r.average_rating.toFixed(1) : r.average_rating}
                    {r.num_ratings && (
                      <span style={{ marginLeft: "0.5rem", opacity: 0.7, fontSize: "0.9em" }}>
                        ({typeof r.num_ratings === 'number' ? r.num_ratings.toLocaleString() : r.num_ratings})
                      </span>
                    )}
                  </span>
                )}
              </div>
              {r.language_dependence && r.language_dependence.level >= 4 && (
                <div style={{ 
                  marginTop: "0.5rem", 
                  padding: "0.5rem", 
                  backgroundColor: "#fff3cd", 
                  border: "1px solid #ffc107",
                  borderRadius: "4px",
                  fontSize: "0.9em",
                  color: "#856404"
                }}>
                  ⚠️ High language dependence (Level {r.language_dependence.level}): {r.language_dependence.value || "Extensive use of text"}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default PistaChat;
