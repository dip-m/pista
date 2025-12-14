// frontend/src/components/PistaChat.jsx
import React from "react";

function PistaChat({ user }) {
  const [messages, setMessages] = React.useState([]);
  const [input, setInput] = React.useState("");
  const [chips, setChips] = React.useState([]);
  const [useCollection, setUseCollection] = React.useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);

    const context = {
      last_game_id: null, // optional: you can track last base_game_id
      useCollection,
    };

    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: user.id,
        message: input,
        context,
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
  };

  return (
    <div className="pista-chat">
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
      </div>

      <div className="chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask: 'Games in my collection closest to Brass: Birmingham but different theme'"
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

function MessageList({ messages }) {
  return (
    <div className="messages">
      {messages.map((m, idx) => (
        <div key={idx} className={`msg msg--${m.role}`}>
          <div className="msg-text">{m.text}</div>
          {m.results && m.results.length > 0 && (
            <GameResultList results={m.results} />
          )}
        </div>
      ))}
    </div>
  );
}

function GameResultList({ results }) {
  return (
    <div className="game-results">
      {results.map((r) => (
        <div className="game-card" key={r.game_id}>
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
          </div>
        </div>
      ))}
    </div>
  );
}

export default PistaChat;
