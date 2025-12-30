// frontend/src/components/features/FeatureBlacklistAdmin.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";

function FeatureBlacklistAdmin({ user }) {
  const navigate = useNavigate();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [keywordPhrase, setKeywordPhrase] = useState("");
  const [featureType, setFeatureType] = useState("");
  const [matchType, setMatchType] = useState("partial");
  const [matches, setMatches] = useState({});
  const [searching, setSearching] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/feature-blacklist`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setRules(data.rules || []);
      } else if (res.status === 403) {
        alert("Admin access required");
        navigate("/");
      }
    } catch (err) {
      console.error("Failed to load blacklist rules:", err);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleSearchMatches = async () => {
    if (!keywordPhrase.trim()) {
      alert("Please enter a keyword phrase");
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(`${API_BASE}/admin/feature-blacklist/search`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          keyword_phrase: keywordPhrase,
          feature_type: featureType || null,
          match_type: matchType,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setMatches(data.matches || {});
      } else {
        alert("Failed to search for matches");
      }
    } catch (err) {
      console.error("Failed to search matches:", err);
      alert("Failed to search for matches");
    } finally {
      setSearching(false);
    }
  };

  const handleAddRule = async () => {
    if (!keywordPhrase.trim()) {
      alert("Please enter a keyword phrase");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/admin/feature-blacklist`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          keyword_phrase: keywordPhrase,
          feature_type: featureType || null,
          match_type: matchType,
        }),
      });
      if (res.ok) {
        await loadRules();
        setShowAddForm(false);
        setKeywordPhrase("");
        setFeatureType("");
        setMatchType("partial");
        setMatches({});
      } else {
        const error = await res.json();
        alert(error.detail || "Failed to add rule");
      }
    } catch (err) {
      console.error("Failed to add rule:", err);
      alert("Failed to add rule");
    }
  };

  const handleToggleRule = async (ruleId) => {
    try {
      const res = await fetch(`${API_BASE}/admin/feature-blacklist/${ruleId}/toggle`, {
        method: "POST",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        await loadRules();
      } else {
        alert("Failed to toggle rule");
      }
    } catch (err) {
      console.error("Failed to toggle rule:", err);
      alert("Failed to toggle rule");
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm("Are you sure you want to delete this rule?")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/admin/feature-blacklist/${ruleId}`, {
        method: "DELETE",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        await loadRules();
      } else {
        alert("Failed to delete rule");
      }
    } catch (err) {
      console.error("Failed to delete rule:", err);
      alert("Failed to delete rule");
    }
  };

  if (loading) {
    return <div className="admin-blacklist-page">Loading...</div>;
  }

  return (
    <div className="admin-blacklist-page">
      <div className="admin-blacklist">
        <div className="admin-blacklist-header">
          <h2>Feature Blacklist Management</h2>
          <button onClick={() => navigate("/")} className="close-button">
            ×
          </button>
        </div>

        <div className="admin-blacklist-actions">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="add-rule-button"
          >
            {showAddForm ? "Cancel" : "+ Add Blacklist Rule"}
          </button>
        </div>

        {showAddForm && (
          <div className="admin-blacklist-form">
            <h3>Add New Blacklist Rule</h3>
            <div className="form-group">
              <label>Keyword/Phrase:</label>
              <input
                type="text"
                value={keywordPhrase}
                onChange={(e) => setKeywordPhrase(e.target.value)}
                placeholder="e.g., Digital Implementation, Countries"
              />
            </div>
            <div className="form-group">
              <label>Feature Type (optional):</label>
              <select
                value={featureType}
                onChange={(e) => setFeatureType(e.target.value)}
              >
                <option value="">All Types</option>
                <option value="mechanics">Mechanics</option>
                <option value="categories">Categories</option>
                <option value="families">Families</option>
                <option value="designers">Designers</option>
                <option value="artists">Artists</option>
                <option value="publishers">Publishers</option>
              </select>
            </div>
            <div className="form-group">
              <label>Match Type:</label>
              <select
                value={matchType}
                onChange={(e) => setMatchType(e.target.value)}
              >
                <option value="partial">Partial Match (contains)</option>
                <option value="exact">Exact Match</option>
              </select>
            </div>
            <div className="form-group">
              <button
                onClick={handleSearchMatches}
                disabled={searching || !keywordPhrase.trim()}
                className="search-matches-button"
              >
                {searching ? "Searching..." : "Preview Matches"}
              </button>
            </div>
            {Object.keys(matches).length > 0 && (
              <div className="matches-preview">
                <h4>Matching Features:</h4>
                {Object.entries(matches).map(([type, features]) => (
                  <div key={type} className="match-group">
                    <strong>{type}:</strong>
                    <ul>
                      {features.map((f) => (
                        <li key={f.id}>{f.name}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
            <div className="form-actions">
              <button onClick={handleAddRule} className="submit-button">
                Add Rule
              </button>
            </div>
          </div>
        )}

        <div className="admin-blacklist-list">
          <h3>Active Blacklist Rules</h3>
          {rules.length === 0 ? (
            <div className="empty-state">No blacklist rules found</div>
          ) : (
            <table className="blacklist-table">
              <thead>
                <tr>
                  <th>Keyword/Phrase</th>
                  <th>Feature Type</th>
                  <th>Match Type</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id} className={rule.is_active ? "" : "inactive"}>
                    <td>{rule.keyword_phrase}</td>
                    <td>{rule.feature_type || "All"}</td>
                    <td>{rule.match_type}</td>
                    <td>
                      <span className={`status-badge ${rule.is_active ? "active" : "inactive"}`}>
                        {rule.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td>{new Date(rule.created_at).toLocaleDateString()}</td>
                    <td>
                      <button
                        onClick={() => handleToggleRule(rule.id)}
                        className="toggle-button"
                      >
                        {rule.is_active ? "Deactivate" : "Activate"}
                      </button>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="delete-button"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default FeatureBlacklistAdmin;
