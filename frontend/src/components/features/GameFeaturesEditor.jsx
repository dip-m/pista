// frontend/src/components/features/GameFeaturesEditor.jsx
import React, { useState, useEffect } from "react";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";

function GameFeaturesEditor({ gameId, gameName, onClose }) {
  const [features, setFeatures] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState("mechanics");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadFeatures();
  }, [gameId]);

  const loadFeatures = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/games/${gameId}/features`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setFeatures(data);
      }
    } catch (err) {
      console.error("Failed to load features:", err);
    } finally {
      setLoading(false);
    }
  };

  const modifyFeature = async (featureType, featureId, action) => {
    try {
      const res = await fetch(
        `${API_BASE}/games/${gameId}/features/modify?feature_type=${featureType}&feature_id=${featureId}&action=${action}`,
        {
          method: "POST",
          headers: authService.getAuthHeaders(),
        }
      );
      if (res.ok) {
        await loadFeatures(); // Reload features
      } else {
        const error = await res.json();
        alert(error.detail || "Failed to modify feature");
      }
    } catch (err) {
      console.error("Failed to modify feature:", err);
      alert("Failed to modify feature");
    }
  };

  const removeModification = async (modId) => {
    try {
      const res = await fetch(
        `${API_BASE}/games/${gameId}/features/modify/${modId}`,
        {
          method: "DELETE",
          headers: authService.getAuthHeaders(),
        }
      );
      if (res.ok) {
        await loadFeatures(); // Reload features
      }
    } catch (err) {
      console.error("Failed to remove modification:", err);
    }
  };

  if (loading) {
    return (
      <div className="game-features-editor">
        <div className="loading">Loading features...</div>
      </div>
    );
  }

  if (!features) {
    return (
      <div className="game-features-editor">
        <div className="error">Failed to load features</div>
      </div>
    );
  }

  const featureTypes = [
    { key: "mechanics", label: "Mechanics" },
    { key: "categories", label: "Categories" },
    { key: "designers", label: "Designers" },
    { key: "artists", label: "Artists" },
    { key: "publishers", label: "Publishers" },
    { key: "families", label: "Families" },
  ];

  const originalFeatures = features.original_features[selectedType] || [];
  const finalFeatures = features.final_features[selectedType] || [];
  const availableFeatures = features.available_features[selectedType] || [];
  const modifications = features.modifications.filter(
    (m) => m.feature_type === selectedType
  );

  const filteredAvailable = availableFeatures.filter((f) =>
    f.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="game-features-editor-overlay" onClick={onClose}>
      <div
        className="game-features-editor"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="features-header">
          <h2>Edit Features: {gameName}</h2>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="features-tabs">
          {featureTypes.map((type) => (
            <button
              key={type.key}
              className={`tab-button ${selectedType === type.key ? "active" : ""}`}
              onClick={() => {
                setSelectedType(type.key);
                setSearchTerm("");
              }}
            >
              {type.label}
            </button>
          ))}
        </div>

        <div className="features-content">
          <div className="features-section">
            <h3>Current Features (with modifications)</h3>
            <div className="feature-list">
              {finalFeatures.length === 0 ? (
                <div className="empty-state">No features</div>
              ) : (
                finalFeatures.map((featureName) => {
                  const feature = availableFeatures.find(
                    (f) => f.name === featureName
                  );
                  const isOriginal = originalFeatures.includes(featureName);
                  const mod = modifications.find(
                    (m) =>
                      availableFeatures.find((f) => f.id === m.feature_id)
                        ?.name === featureName
                  );
                  return (
                    <div
                      key={featureName}
                      className={`feature-item ${isOriginal ? "original" : "modified"}`}
                    >
                      <span>{featureName}</span>
                      {!isOriginal && mod && (
                        <button
                          className="remove-mod-btn"
                          onClick={() => removeModification(mod.id)}
                          title="Remove modification"
                        >
                          ↶
                        </button>
                      )}
                      {isOriginal && (
                        <button
                          className="remove-btn"
                          onClick={() =>
                            feature &&
                            modifyFeature(selectedType, feature.id, "remove")
                          }
                          title="Remove feature"
                        >
                          −
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="features-section">
            <h3>Add Features</h3>
            <input
              type="text"
              placeholder="Search features..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="feature-search"
            />
            <div className="feature-list">
              {filteredAvailable
                .filter(
                  (f) =>
                    !finalFeatures.includes(f.name) ||
                    modifications.some(
                      (m) =>
                        m.feature_id === f.id && m.action === "remove"
                    )
                )
                .map((feature) => (
                  <div key={feature.id} className="feature-item available">
                    <span>{feature.name}</span>
                    <button
                      className="add-btn"
                      onClick={() =>
                        modifyFeature(selectedType, feature.id, "add")
                      }
                      title="Add feature"
                    >
                      +
                    </button>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GameFeaturesEditor;

