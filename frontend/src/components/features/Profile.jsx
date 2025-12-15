// frontend/src/components/features/Profile.jsx
import React, { useState, useEffect, useCallback } from "react";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";

function Profile({ user, onUserUpdate }) {
  const [collection, setCollection] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [bggId, setBggId] = useState(user.bgg_id || ""); // Add local state for BGG ID
  const [sortBy, setSortBy] = useState("year_published");
  const [sortOrder, setSortOrder] = useState("desc");
  const [collectionSearchQuery, setCollectionSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(12);

  const loadCollection = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/profile/collection?sort_by=${sortBy}&order=${sortOrder}`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setCollection(data);
      }
    } catch (err) {
      console.error("Failed to load collection:", err);
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortOrder]);

  useEffect(() => {
    loadCollection();
  }, [loadCollection]);

  // Update bggId when user prop changes
  useEffect(() => {
    setBggId(user.bgg_id || "");
  }, [user.bgg_id]);

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    try {
      const res = await fetch(`${API_BASE}/games/search?q=${encodeURIComponent(query)}&limit=10`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearchLoading(false);
    }
  };

  // Filter collection based on search query
  const filteredCollection = collection.filter(game => 
    !collectionSearchQuery || 
    game.name.toLowerCase().includes(collectionSearchQuery.toLowerCase())
  );

  // Pagination calculations
  const totalPages = Math.ceil(filteredCollection.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedCollection = filteredCollection.slice(startIndex, endIndex);

  // Reset to page 1 when search query or items per page changes
  useEffect(() => {
    setCurrentPage(1);
  }, [collectionSearchQuery, itemsPerPage]);

  const addToCollection = async (gameId) => {
    try {
      const res = await fetch(`${API_BASE}/profile/collection`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ game_id: gameId }),
      });
      if (res.ok) {
        await loadCollection();
        setSearchQuery("");
        setSearchResults([]);
      } else {
        const error = await res.json();
        alert(error.detail || "Failed to add game");
      }
    } catch (err) {
      console.error("Failed to add game:", err);
      alert("Failed to add game");
    }
  };

  const removeFromCollection = async (gameId) => {
    try {
      const res = await fetch(`${API_BASE}/profile/collection/${gameId}`, {
        method: "DELETE",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        await loadCollection();
      } else {
        alert("Failed to remove game");
      }
    } catch (err) {
      console.error("Failed to remove game:", err);
      alert("Failed to remove game");
    }
  };

  const isInCollection = (gameId) => {
    return collection.some((g) => g.game_id === gameId);
  };

  return (
    <div className="profile-container">
      <div className="profile-header">
        <h2>Profile</h2>
        <div className="user-info">
          <p>
            <strong>Username:</strong> {user.username}
          </p>
          <div className="bgg-id-section">
            <label>
              <strong>BGG Username/ID:</strong>
              <input
                type="text"
                value={bggId}
                onChange={(e) => setBggId(e.target.value)}
                placeholder="Enter your BGG username or ID"
                onBlur={async (e) => {
                  const bggIdValue = e.target.value.trim() || null;
                  // #region agent log
                  console.log('[DEBUG] BGG ID onBlur:', {bggIdValue, currentBggId: user.bgg_id, localBggId: bggId});
                  fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:123','message':'BGG ID onBlur triggered',data:{bggIdValue,currentBggId:user.bgg_id,localBggId:bggId},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'A'})}).catch(()=>{});
                  // #endregion
                  
                  // Only update if value actually changed
                  if (bggIdValue === (user.bgg_id || "")) {
                    console.log('[DEBUG] BGG ID unchanged, skipping update');
                    return;
                  }
                  
                  try {
                    console.log('[DEBUG] Sending BGG ID update request:', bggIdValue);
                    const res = await fetch(`${API_BASE}/profile/bgg-id`, {
                      method: "PUT",
                      headers: {
                        ...authService.getAuthHeaders(),
                        "Content-Type": "application/json",
                      },
                      body: JSON.stringify({ bgg_id: bggIdValue }),
                    });
                    // #region agent log
                    console.log('[DEBUG] BGG ID API response:', {status: res.status, ok: res.ok});
                    fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:134','message':'BGG ID API response',data:{status:res.status,ok:res.ok},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'A'})}).catch(()=>{});
                    // #endregion
                    if (res.ok) {
                      const data = await res.json();
                      // #region agent log
                      console.log('[DEBUG] BGG ID update success:', data);
                      fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:137','message':'BGG ID update success',data:{bgg_id:data.bgg_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'A'})}).catch(()=>{});
                      // #endregion
                      // Update local state to match server response
                      setBggId(data.bgg_id || "");
                      // Update user object and notify parent
                      user.bgg_id = data.bgg_id;
                      // Refresh user data from server to ensure consistency
                      if (onUserUpdate) {
                        await onUserUpdate();
                      }
                    } else {
                      const error = await res.json();
                      // #region agent log
                      console.error('[DEBUG] BGG ID update error:', error);
                      fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:142','message':'BGG ID update error',data:{error:error.detail},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'A'})}).catch(()=>{});
                      // #endregion
                      alert(error.detail || "Failed to update BGG ID");
                      // Revert to original value on error
                      setBggId(user.bgg_id || "");
                    }
                  } catch (err) {
                    // #region agent log
                    console.error('[DEBUG] BGG ID update exception:', err);
                    fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:147','message':'BGG ID update exception',data:{error:err.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'A'})}).catch(()=>{});
                    // #endregion
                    alert("Failed to update BGG ID: " + err.message);
                    // Revert to original value on error
                    setBggId(user.bgg_id || "");
                  }
                }}
              />
            </label>
            {(bggId || user.bgg_id) && (
              <button
                onClick={async () => {
                  // #region agent log
                  console.log('[DEBUG] Import button clicked:', {bggId, userBggId: user.bgg_id});
                  fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:183','message':'Import button clicked',data:{bggId,userBggId:user.bgg_id},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'C'})}).catch(()=>{});
                  // #endregion
                  if (!window.confirm("This will import/update your collection from BGG. Continue?")) {
                    return;
                  }
                  try {
                    console.log('[DEBUG] Sending import request');
                    const res = await fetch(`${API_BASE}/profile/collection/import-bgg`, {
                      method: "POST",
                      headers: authService.getAuthHeaders(),
                    });
                    // #region agent log
                    console.log('[DEBUG] Import API response:', {status: res.status, ok: res.ok});
                    fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:191','message':'Import API response',data:{status:res.status,ok:res.ok},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'C'})}).catch(()=>{});
                    // #endregion
                    if (res.ok) {
                      const data = await res.json();
                      // #region agent log
                      console.log('[DEBUG] Import success:', data);
                      fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:194','message':'Import success',data:{added:data.added,skipped:data.skipped},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'C'})}).catch(()=>{});
                      // #endregion
                      alert(`Imported ${data.added} games from BGG! (${data.skipped} skipped)`);
                      await loadCollection();
                    } else {
                      const error = await res.json();
                      // #region agent log
                      console.error('[DEBUG] Import error:', error);
                      fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:199','message':'Import error',data:{error:error.detail},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'C'})}).catch(()=>{});
                      // #endregion
                      alert(error.detail || "Failed to import collection");
                    }
                  } catch (err) {
                    // #region agent log
                    console.error('[DEBUG] Import exception:', err);
                    fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Profile.jsx:203','message':'Import exception',data:{error:err.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'C'})}).catch(()=>{});
                    // #endregion
                    alert("Failed to import collection: " + err.message);
                  }
                }}
                className="import-bgg-button"
              >
                Import/Update Collection from BGG
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="profile-section">
        <h3>Add Games to Collection</h3>
        <div className="game-search">
          <input
            type="text"
            placeholder="Search for games..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="search-input"
          />
          {searchLoading && <div className="loading">Searching...</div>}
          {searchResults.length > 0 && (
            <div className="search-results">
              {searchResults.map((game) => (
                <div key={game.id} className="search-result-item">
                  <div className="game-info">
                    <strong>{game.name}</strong>
                    {game.year_published && <span> ({game.year_published})</span>}
                  </div>
                  {isInCollection(game.id) ? (
                    <span className="in-collection">In Collection</span>
                  ) : (
                    <button onClick={() => addToCollection(game.id)} className="add-button">
                      Add
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="profile-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "1rem" }}>
          <h3>My Collection ({collection.length})</h3>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="Search collection..."
              value={collectionSearchQuery}
              onChange={(e) => setCollectionSearchQuery(e.target.value)}
              style={{ padding: "0.5rem", borderRadius: "4px", border: "1px solid #ccc" }}
            />
            <label>
              Sort by:
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={{ marginLeft: "0.5rem", padding: "0.25rem" }}>
                <option value="added_at">Date Added</option>
                <option value="name">Name</option>
                <option value="year_published">Year</option>
                <option value="average_rating">Rating</option>
              </select>
            </label>
            <label>
              Order:
              <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} style={{ marginLeft: "0.5rem", padding: "0.25rem" }}>
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </label>
            <label>
              Per page:
              <select value={itemsPerPage} onChange={(e) => setItemsPerPage(Number(e.target.value))} style={{ marginLeft: "0.5rem", padding: "0.25rem" }}>
                <option value="6">6</option>
                <option value="12">12</option>
                <option value="24">24</option>
                <option value="48">48</option>
                <option value="96">96</option>
              </select>
            </label>
          </div>
        </div>
        {loading ? (
          <div className="loading">Loading collection...</div>
        ) : collection.length === 0 ? (
          <p className="empty-state">Your collection is empty. Search for games above to add them!</p>
        ) : (
          <>
            <div className="collection-grid">
              {paginatedCollection.map((game) => (
                <div key={game.game_id} className="collection-tile">
                  <div className="tile-image-container">
                    {game.thumbnail ? (
                      <img src={game.thumbnail} alt={game.name} className="tile-image" />
                    ) : (
                      <div className="tile-image-placeholder">No Image</div>
                    )}
                  </div>
                  <div className="tile-content">
                    <div className="tile-name">
                      {game.name}
                      {game.year_published && ` (${game.year_published})`}
                    </div>
                    <div className="tile-meta">
                      {game.personal_rating ? (
                        <div className="tile-personal-rating">
                          💫 Personal: {game.personal_rating.toFixed(1)}
                        </div>
                      ) : game.average_rating && (
                        <div className="tile-rating">
                          ⭐ BGG: {game.average_rating.toFixed(1)}
                        </div>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => removeFromCollection(game.game_id)}
                    className="tile-remove-button"
                    title="Remove from collection"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            {totalPages > 1 && (
              <div className="pagination-controls">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="pagination-button"
                >
                  Previous
                </button>
                <span className="pagination-info">
                  Page {currentPage} of {totalPages} ({filteredCollection.length} games)
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="pagination-button"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Profile;

