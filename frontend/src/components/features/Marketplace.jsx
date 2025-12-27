// frontend/src/components/features/Marketplace.jsx
import React, { useState, useEffect } from "react";
import { API_BASE } from "../../config/api";
import { authService } from "../../services/auth";

function Marketplace({ gameId, gameName, onClose }) {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (gameId) {
      fetchMarketplaceListings(gameId);
    }
  }, [gameId]);

  const fetchMarketplaceListings = async (gameId) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/marketplace/search?game_id=${gameId}`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setListings(data.listings || []);
      } else {
        setError("Failed to fetch marketplace listings");
      }
    } catch (err) {
      console.error("Marketplace fetch error:", err);
      setError("Error loading marketplace data");
    } finally {
      setLoading(false);
    }
  };

  const getPlatformIcon = (platform) => {
    const icons = {
      amazon: "📦",
      ebay: "🏪",
      geekmarket: "🎲",
      wallapop: "🛒",
    };
    return icons[platform.toLowerCase()] || "🛍️";
  };

  const getConditionBadge = (condition) => {
    const colors = {
      new: "#4caf50",
      "like new": "#8bc34a",
      used: "#ff9800",
      "fair": "#ff5722",
    };
    const color = colors[condition?.toLowerCase()] || "#999";
    return { backgroundColor: color, color: "white", padding: "2px 8px", borderRadius: "4px", fontSize: "0.75rem" };
  };

  return (
    <div className="marketplace-sidebar">
      <div className="marketplace-header">
        <h3>Marketplace: {gameName}</h3>
        <button onClick={onClose} className="marketplace-close">×</button>
      </div>
      {loading ? (
        <div className="marketplace-loading">Loading listings...</div>
      ) : error ? (
        <div className="marketplace-error">{error}</div>
      ) : listings.length === 0 ? (
        <div className="marketplace-empty">No listings found for this game.</div>
      ) : (
        <div className="marketplace-listings">
          {listings.map((listing, idx) => (
            <div key={idx} className="marketplace-listing">
              <div className="listing-header">
                <span className="listing-platform">
                  {getPlatformIcon(listing.platform)} {listing.platform}
                </span>
                {listing.condition && (
                  <span style={getConditionBadge(listing.condition)}>
                    {listing.condition}
                  </span>
                )}
              </div>
              <div className="listing-price">
                {listing.currency || "$"}{listing.price?.toFixed(2)}
                {listing.shipping_included && <span className="shipping-note"> (shipping included)</span>}
              </div>
              {listing.seller_rating && (
                <div className="listing-rating">
                  Seller: ⭐ {listing.seller_rating.toFixed(1)} ({listing.seller_reviews || 0} reviews)
                </div>
              )}
              {listing.location && (
                <div className="listing-location">📍 Ships from: {listing.location}</div>
              )}
              {listing.url && (
                <a
                  href={listing.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="listing-link"
                >
                  View Listing →
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Marketplace;
