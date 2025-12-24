// frontend/src/components/features/ABTestAdmin.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";

function ABTestAdmin({ user }) {
  const navigate = useNavigate();
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingConfig, setEditingConfig] = useState(null);
  const [configKey, setConfigKey] = useState("");
  const [configValue, setConfigValue] = useState("");
  const [isActive, setIsActive] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/ab-test-configs`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setConfigs(data.configs);
      } else if (res.status === 403) {
        alert("Admin access required");
        navigate("/");
      }
    } catch (err) {
      console.error("Failed to load A/B test configs:", err);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!configKey.trim()) {
      alert("Config key is required");
      return;
    }

    try {
      // Validate JSON
      let parsedValue = configValue;
      try {
        parsedValue = JSON.parse(configValue);
      } catch {
        alert("Config value must be valid JSON");
        return;
      }

      const res = await fetch(
        `${API_BASE}/admin/ab-test-configs?config_key=${encodeURIComponent(configKey)}&config_value=${encodeURIComponent(JSON.stringify(parsedValue))}&is_active=${isActive}`,
        {
          method: "POST",
          headers: authService.getAuthHeaders(),
        }
      );
      if (res.ok) {
        await loadConfigs();
        resetForm();
      } else {
        alert("Failed to save config");
      }
    } catch (err) {
      console.error("Failed to save config:", err);
      alert("Failed to save config");
    }
  };

  const resetForm = () => {
    setEditingConfig(null);
    setConfigKey("");
    setConfigValue("");
    setIsActive(false);
    setShowAddForm(false);
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    setConfigKey(config.config_key);
    setConfigValue(JSON.stringify(config.config_value, null, 2));
    setIsActive(config.is_active);
    setShowAddForm(true);
  };

  const handleToggle = async (configKey, currentActive) => {
    try {
      const res = await fetch(
        `${API_BASE}/admin/ab-test-configs/${configKey}?is_active=${!currentActive}`,
        {
          method: "PUT",
          headers: authService.getAuthHeaders(),
        }
      );
      if (res.ok) {
        await loadConfigs();
      } else {
        alert("Failed to toggle config");
      }
    } catch (err) {
      console.error("Failed to toggle config:", err);
      alert("Failed to toggle config");
    }
  };

  const handleDelete = async (configKeyToDelete) => {
    if (!window.confirm("Are you sure you want to delete this A/B test config?")) return;

    try {
      const res = await fetch(`${API_BASE}/admin/ab-test-configs/${configKeyToDelete}`, {
        method: "DELETE",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        await loadConfigs();
      } else {
        alert("Failed to delete config");
      }
    } catch (err) {
      console.error("Failed to delete config:", err);
      alert("Failed to delete config");
    }
  };

  return (
    <div className="admin-feedback-page">
      <div className="admin-feedback-container">
        <div className="admin-feedback-header">
          <h2>Admin: A/B Test Configs</h2>
          <button className="close-button" onClick={() => navigate("/")}>×</button>
        </div>

        {showAddForm ? (
          <div className="admin-feedback-form">
            <h3>{editingConfig ? "Edit A/B Test Config" : "Add New A/B Test Config"}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Config Key:</label>
                <input
                  type="text"
                  value={configKey}
                  onChange={(e) => setConfigKey(e.target.value)}
                  placeholder="e.g., use_rarity_weighting"
                  required
                  disabled={!!editingConfig}
                />
              </div>
              <div className="form-group">
                <label>Config Value (JSON):</label>
                <textarea
                  value={configValue}
                  onChange={(e) => setConfigValue(e.target.value)}
                  placeholder='{"enabled": true, "name": "Rarity Weighting", "label_a": "Standard", "label_b": "Rarity Weighted", "question_text": "Which results do you prefer?"}'
                  rows={8}
                  required
                />
                <small style={{ color: "#666", fontSize: "0.85rem" }}>
                  JSON object with: enabled (bool), name (string), label_a (string), label_b (string), question_text (string, optional)
                </small>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                  />
                  Active (enables A/B testing)
                </label>
              </div>
              <div className="form-actions">
                <button type="submit" className="submit-btn">
                  {editingConfig ? "Update" : "Create"}
                </button>
                <button type="button" onClick={resetForm} className="cancel-btn">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            <div className="admin-feedback-actions">
              <button onClick={() => setShowAddForm(true)} className="add-btn">
                + Add A/B Test Config
              </button>
            </div>
            {loading ? (
              <div className="loading">Loading configs...</div>
            ) : (
              <div className="admin-feedback-list">
                {configs.length === 0 ? (
                  <div className="empty-state">No A/B test configs yet. Add one to get started.</div>
                ) : (
                  configs.map((config) => (
                    <div key={config.id} className="feedback-question-item">
                      <div className="question-header">
                        <span className={`question-status ${config.is_active ? "active" : "inactive"}`}>
                          {config.is_active ? "✓" : "○"}
                        </span>
                        <h4>{config.config_key}</h4>
                      </div>
                      <div className="question-options">
                        <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap", margin: "0.5rem 0" }}>
                          {JSON.stringify(config.config_value, null, 2)}
                        </pre>
                      </div>
                      <div className="question-actions">
                        <button
                          onClick={() => handleToggle(config.config_key, config.is_active)}
                          className={config.is_active ? "edit-btn" : "cancel-btn"}
                        >
                          {config.is_active ? "Disable" : "Enable"}
                        </button>
                        <button onClick={() => handleEdit(config)} className="edit-btn">
                          Edit
                        </button>
                        <button onClick={() => handleDelete(config.config_key)} className="delete-btn">
                          Delete
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ABTestAdmin;
