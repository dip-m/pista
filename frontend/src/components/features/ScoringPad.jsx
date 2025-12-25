// frontend/src/components/features/ScoringPad.jsx
import React, { useState, useEffect, useCallback } from "react";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";

function ScoringPad({ game, onClose }) {
  const [mechanism, setMechanism] = useState(game.mechanism || null);
  const [intermediateScores, setIntermediateScores] = useState({});
  const [calculatedScores, setCalculatedScores] = useState([]);
  const [finalScore, setFinalScore] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadMechanism = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/scoring/mechanism/${game.id}`, {
        headers: authService.getAuthHeaders(),
      });
      const data = await res.json();
      if (data.exists && data.mechanism) {
        setMechanism(data.mechanism);
      }
    } catch (err) {
      console.error("Failed to load scoring mechanism:", err);
    }
  }, [game.id]);

  useEffect(() => {
    // Load mechanism if not provided
    if (!mechanism && game.id) {
      loadMechanism();
    }
  }, [game.id, mechanism, loadMechanism]);

  const handleInputChange = (scoreId, value) => {
    setIntermediateScores((prev) => ({
      ...prev,
      [scoreId]: value,
    }));
    setCalculatedScores([]);
    setFinalScore(null);
    setSaved(false);
  };

  const calculateScore = async () => {
    if (!mechanism) return;

    setIsCalculating(true);
    try {
      const res = await fetch(`${API_BASE}/scoring/calculate`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          game_id: game.id,
          mechanism_id: mechanism.id,
          intermediate_scores: intermediateScores,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setCalculatedScores(data.intermediate_scores || []);
        setFinalScore(data.final_score || 0);
      } else {
        alert("Failed to calculate score");
      }
    } catch (err) {
      console.error("Failed to calculate score:", err);
      alert("Failed to calculate score");
    } finally {
      setIsCalculating(false);
    }
  };

  const saveSession = async () => {
    if (!mechanism || finalScore === null) return;

    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE}/scoring/save`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          game_id: game.id,
          mechanism_id: mechanism.id,
          intermediate_scores: intermediateScores,
          final_score: finalScore,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } else {
        alert("Failed to save scoring session");
      }
    } catch (err) {
      console.error("Failed to save scoring session:", err);
      alert("Failed to save scoring session");
    } finally {
      setIsSaving(false);
    }
  };

  if (!mechanism) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "600px" }}>
          <div className="modal-header">
            <h2>Scoring Pad - {game.name}</h2>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            <p>Scoring mechanism not available for this game yet.</p>
            <p>Please check back later or contact support if you believe this game should have scoring.</p>
          </div>
        </div>
      </div>
    );
  }

  const criteria = mechanism.criteria || {};
  const intermediateScoresList = criteria.intermediate_scores || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "700px", maxHeight: "90vh", overflowY: "auto" }}>
        <div className="modal-header">
          <h2>End-Game Scoring - {game.name}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ marginBottom: "1rem", fontSize: "1.2rem" }}>Enter Your Game State</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {intermediateScoresList.map((scoreDef) => {
                const scoreId = scoreDef.id;
                const label = scoreDef.label;
                const inputType = scoreDef.input_type || "number";
                const description = scoreDef.description || "";
                const currentValue = intermediateScores[scoreId] || "";

                return (
                  <div key={scoreId} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    <label style={{ fontWeight: "500", fontSize: "0.95rem" }}>
                      {label}
                      {description && (
                        <span style={{ fontSize: "0.85rem", color: "#666", marginLeft: "0.5rem" }}>
                          ({description})
                        </span>
                      )}
                    </label>
                    <input
                      type={inputType}
                      value={currentValue}
                      onChange={(e) => handleInputChange(scoreId, e.target.value)}
                      placeholder="Enter value"
                      style={{
                        padding: "0.5rem",
                        border: "1px solid #ddd",
                        borderRadius: "4px",
                        fontSize: "1rem",
                      }}
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {calculatedScores.length > 0 && (
            <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#f5f5f5", borderRadius: "4px" }}>
              <h3 style={{ marginBottom: "0.75rem", fontSize: "1.1rem" }}>Calculated Scores</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {calculatedScores.map((score, idx) => (
                  <div key={idx} style={{ display: "flex", justifyContent: "space-between", padding: "0.5rem" }}>
                    <span>{score.label}:</span>
                    <span style={{ fontWeight: "500" }}>{score.value.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {finalScore !== null && (
            <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#e3f2fd", borderRadius: "4px", border: "2px solid #2196f3" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0, fontSize: "1.2rem", color: "#1976d2" }}>Final Score:</h3>
                <span style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#1976d2" }}>
                  {finalScore.toFixed(1)}
                </span>
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <button
              onClick={calculateScore}
              disabled={isCalculating || intermediateScoresList.length === 0 || Object.keys(intermediateScores).length === 0}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: "#2196f3",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: isCalculating ? "not-allowed" : "pointer",
                fontSize: "1rem",
                fontWeight: "500",
              }}
            >
              {isCalculating ? "Calculating..." : "Calculate Score"}
            </button>
            {finalScore !== null && (
              <button
                onClick={saveSession}
                disabled={isSaving || saved}
                style={{
                  padding: "0.75rem 1.5rem",
                  backgroundColor: saved ? "#4caf50" : "#ff9800",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: isSaving ? "not-allowed" : "pointer",
                  fontSize: "1rem",
                  fontWeight: "500",
                }}
              >
                {saved ? "✓ Saved" : isSaving ? "Saving..." : "Save Score"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ScoringPad;

