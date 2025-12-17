// frontend/src/components/features/AdminGames.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";
import GameFeaturesEditor from "./GameFeaturesEditor";

function AdminGames({ user }) {
  const navigate = useNavigate();
  
  const handleClose = () => {
    navigate("/");
  };
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGame, setSelectedGame] = useState(null);

  const loadGames = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: "50",
      });
      if (searchQuery) {
        params.append("search", searchQuery);
      }
      
      const res = await fetch(`${API_BASE}/admin/games?${params}`, {
        headers: authService.getAuthHeaders(),
      });
      
      if (res.ok) {
        const data = await res.json();
        setGames(data.games);
        setTotalPages(data.total_pages);
      } else if (res.status === 403) {
        alert("Admin access required");
        handleClose();
      }
    } catch (err) {
      console.error("Failed to load games:", err);
    } finally {
      setLoading(false);
    }
  }, [page, searchQuery]);

  useEffect(() => {
    loadGames();
  }, [loadGames]);

  const handleSearch = (e) => {
    setSearchQuery(e.target.value);
    setPage(1); // Reset to first page on search
  };

  return (
    <div className="admin-games-page">
      <div className="admin-games">
        <div className="admin-games-header">
          <h2>Admin: All Games</h2>
          <button className="close-button" onClick={handleClose}>×</button>
        </div>
        
        <div className="admin-games-search">
          <input
            type="text"
            placeholder="Search games..."
            value={searchQuery}
            onChange={handleSearch}
            className="admin-search-input"
          />
        </div>
        
        {loading ? (
          <div className="loading">Loading games...</div>
        ) : (
          <>
            <div className="admin-games-list">
              {games.map((game) => (
                <div
                  key={game.id}
                  className="admin-game-item"
                  onClick={() => setSelectedGame(game)}
                >
                  {game.thumbnail && (
                    <img
                      src={game.thumbnail}
                      alt={game.name}
                      className="admin-game-thumbnail"
                    />
                  )}
                  <div className="admin-game-info">
                    <div className="admin-game-name">{game.name}</div>
                    {game.year_published && (
                      <div className="admin-game-year">{game.year_published}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="admin-games-pagination">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
      
      {selectedGame && (
        <GameFeaturesEditor
          gameId={selectedGame.id}
          gameName={selectedGame.name}
          onClose={() => setSelectedGame(null)}
        />
      )}
    </div>
  );
}

export default AdminGames;


