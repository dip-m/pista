// frontend/src/components/features/PistaChat.jsx
import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";
import { httpRequest } from "../../utils/httpClient";
import Marketplace from "./Marketplace";
import GameFeaturesEditor from "./GameFeaturesEditor";
import ScoringPad from "./ScoringPad";
import { hasExceededLimit, incrementMessageCount, getRemainingMessages } from "../../utils/anonymousUser";

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
  const [doINeedChips, setDoINeedChips] = useState([]); // [{id, name, game_id}, ...]
  const [excludeSameSeries, setExcludeSameSeries] = useState(false); // Exclude same series/families
  const [excludedFamilies, setExcludedFamilies] = useState([]); // Families to exclude
  const [excludeImplementationCategories, setExcludeImplementationCategories] = useState(false); // Exclude implementation categories
  const [useCollection, setUseCollection] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false); // Start collapsed
  const [showFiltersOverlay, setShowFiltersOverlay] = useState(false); // Overlay for text tiles
  const [playerCount, setPlayerCount] = useState(null); // Single player count selector
  const [playtime, setPlaytime] = useState(null); // Single playtime selector
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [gameSearchResults, setGameSearchResults] = useState([]);
  const [featureSearchResults, setFeatureSearchResults] = useState([]);
  const [showGameSearch, setShowGameSearch] = useState(false);
  const [atMentionActive, setAtMentionActive] = useState(false);
  const [atMentionPosition, setAtMentionPosition] = useState(0);
  const [atMentionQuery, setAtMentionQuery] = useState("");
  const searchDebounceTimerRef = useRef(null);
  const [marketplaceGame, setMarketplaceGame] = useState(null);
  const [featuresEditorGame, setFeaturesEditorGame] = useState(null);
  const [scoringPadGame, setScoringPadGame] = useState(null);
  const [helpfulQuestion, setHelpfulQuestion] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProcessingIndicator, setShowProcessingIndicator] = useState(false);
  const [processingTimeout, setProcessingTimeout] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const [requiredFeatures, setRequiredFeatures] = useState({}); // {messageIndex: {mechanics: Set, categories: Set, ...}}
  const [activeRequiredFeatures, setActiveRequiredFeatures] = useState([]); // [{type, value, key, messageIndex}, ...] for display in chips
  const [dislikeDetails, setDislikeDetails] = useState({}); // Store additional details for each message
  const [showDislikeInput, setShowDislikeInput] = useState({}); // Track which messages show input
  const [messageLimitError, setMessageLimitError] = useState(null); // Error message for message limit
  const [showWelcomeMessage, setShowWelcomeMessage] = useState(true); // Show welcome message on first visit
  // eslint-disable-next-line no-unused-vars
  const [userJourneyState, setUserJourneyState] = useState(null); // Track user journey: 'game_in_mind', 'exploring', 'theme_preference', 'mechanics_preference'

  // Note: requiredFeatures state is managed via setRequiredFeatures in handleRequireFeature and removeRequiredFeature

  // Debug: Log state changes for game search
  useEffect(() => {
  }, [atMentionActive, showGameSearch, gameSearchResults.length, featureSearchResults.length]);

  // Auto-format search text when chips or flags change
  // Only format if there are other chips/flags besides just a game (to allow game detail view)
  useEffect(() => {
    // Check if there are other chips/flags besides just games
    const hasOtherFilters = playerChips.length > 0 ||
                            playtimeChips.length > 0 ||
                            activeRequiredFeatures.length > 0 ||
                            useCollection ||
                            excludeSameSeries ||
                            gameChips.length > 1; // Multiple games

    // Never auto-format if there's only a single game with no other filters
    // This allows users to type the game name and get a description
    // Also check if input is just the game name (possibly with trailing space)
    // This prevents auto-formatting when a game is selected from @ dropdown
    const inputTrimmed = input.trim();
    const gameNameTrimmed = gameChips.length === 1 ? gameChips[0].name.trim() : '';
    const isJustGameName = gameChips.length === 1 && gameNameTrimmed &&
                          ((inputTrimmed === gameNameTrimmed) ||
                           (inputTrimmed.startsWith(gameNameTrimmed + ' ') &&
                            inputTrimmed.split(' ').length <= 2)); // Allow game name + one word (like a space or single character)

    if ((!hasOtherFilters && gameChips.length === 1) || isJustGameName) {
      // Single game with no other filters - don't auto-format, allow user to type or get game details
      return;
    }

    // Build a natural language sentence from all chips and flags
    const parts = [];

    // Add games
    if (gameChips.length > 0) {
      if (gameChips.length === 1) {
        parts.push(`games similar to ${gameChips[0].name}`);
      } else {
        const gameNames = gameChips.map(g => g.name).join(', ');
        parts.push(`games similar to ${gameNames}`);
      }
    }

    // Add player count
    if (playerChips.length > 0) {
      const playerCount = playerChips[0];
      parts.push(`for ${playerCount} ${playerCount === 1 ? 'player' : 'players'}`);
    }

    // Add playtime
    if (playtimeChips.length > 0) {
      parts.push(`with ${playtimeChips[0].label.toLowerCase()} playtime`);
    }

    // Add required features
    if (activeRequiredFeatures.length > 0) {
      const featureNames = activeRequiredFeatures.map(f => f.value).join(', ');
      parts.push(`with ${featureNames}`);
    }

    // Add collection flag
    if (useCollection) {
      parts.push('in my collection');
    }

    // Add exclude same series flag
    if (excludeSameSeries) {
      parts.push('excluding same series');
    }

    // Only update if we have at least one chip or flag, and input is empty or matches old format
    if (parts.length > 0) {
      const formattedText = parts.join(' ');
      // Only update if input is empty or doesn't match the formatted text
      // This prevents infinite loops when user is typing
      const currentInput = input.trim();
      if (currentInput === '' || currentInput !== formattedText.trim()) {
        // Use a small delay to avoid conflicts with other input updates
        const timeoutId = setTimeout(() => {
          setInput(formattedText);
        }, 100);
        return () => clearTimeout(timeoutId);
      }
    }
  }, [gameChips, playerChips, playtimeChips, activeRequiredFeatures, useCollection, excludeSameSeries, input]);

  const loadChatHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await httpRequest(`${API_BASE}/chat/history`, {
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
      loadHelpfulQuestion();
    }
  }, [loadChatHistory, user]);

  const loadHelpfulQuestion = async () => {
    try {
      const res = await httpRequest(`${API_BASE}/feedback/questions/helpful`, {
        method: "GET",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const question = await res.json();
        if (question) {
          setHelpfulQuestion(question);
        }
      }
    } catch (err) {
      console.error("Failed to load helpful question:", err);
    }
  };

  const handleGameSearch = useCallback(async (query) => {
    // Allow spaces and multiple keywords - trim but don't restrict
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) {
      setGameSearchResults([]);
      setFeatureSearchResults([]);
      setShowGameSearch(false);
      return;
    }

    // Clear existing debounce timer
    if (searchDebounceTimerRef.current) {
      clearTimeout(searchDebounceTimerRef.current);
    }

    // Debounce search to avoid too many requests
    searchDebounceTimerRef.current = setTimeout(async () => {
      try {
        // Increase limit to 20 for better results
        const searchUrl = `${API_BASE}/games/search?q=${encodeURIComponent(trimmedQuery)}&limit=20`;
        console.log("Searching games:", searchUrl, "API_BASE:", API_BASE);
        const res = await httpRequest(searchUrl, { method: "GET" });
        console.log("Search response status:", res.status, res.ok, "statusText:", res.statusText);
        if (res.ok) {
          const data = await res.json();
          console.log("Search response data:", data);
          // Handle both old format (array) and new format (object with games/features)
          if (Array.isArray(data)) {
            setGameSearchResults(data);
            setFeatureSearchResults([]);
            console.log("Set game results (array format):", data.length);
          } else {
            const games = data.games || [];
            setGameSearchResults(games);
            console.log("Set game results (object format):", games.length);
            // Reorder features: mechanics, categories, designers, artists
            const features = data.features || [];
            const orderedFeatures = [
              ...features.filter(f => f.type === "mechanics"),
              ...features.filter(f => f.type === "categories"),
              ...features.filter(f => f.type === "designers"),
              ...features.filter(f => f.type === "artists"),
              ...features.filter(f => f.type === "publishers" && f.type !== "artists")
            ];
            setFeatureSearchResults(orderedFeatures);
            console.log("Set feature results:", orderedFeatures.length);
          }
          setShowGameSearch(true);
          console.log("Set showGameSearch to true");
        } else {
          console.error("Search request failed:", res.status, res.statusText);
          const errorText = await res.text();
          console.error("Error response:", errorText);
          setShowGameSearch(false);
          setGameSearchResults([]);
          setFeatureSearchResults([]);
        }
      } catch (err) {
        console.error("Search failed with error:", err);
        setShowGameSearch(false);
        setGameSearchResults([]);
        setFeatureSearchResults([]);
      }
    }, 200); // 200ms debounce
  }, []);

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
        // Check if there's a newline after @ (mention completed)
        const hasNewlineAfterAt = textAfterAt.includes('\n');
        // Allow spaces in search query - check if @ is followed by text (can include spaces)
        // Only stop if there's a newline or if cursor moved past the query
        const textAfterCursor = value.substring(cursorPos);
        const fullTextAfterAt = textAfterAt + textAfterCursor;
        // Find where the query ends (newline or end of input)
        const queryEndMatch = fullTextAfterAt.match(/^([^\n]*)/);
        const query = queryEndMatch ? queryEndMatch[1].trim() : textAfterAt.trim();


        if (!hasNewlineAfterAt && query.length >= 0) {
          // @ mention is active - allow spaces in query
          setAtMentionActive(true);
          setAtMentionPosition(lastAtIndex);
          setAtMentionQuery(query); // Store the current query
          console.log("@ mention detected, query:", query, "length:", query.length);
          if (query.length >= 2) {
            console.log("Calling handleGameSearch with:", query);
            handleGameSearch(query);
          } else {
            console.log("Query too short, hiding dropdown");
            setShowGameSearch(false);
            setGameSearchResults([]);
            setFeatureSearchResults([]);
          }
        } else {
          console.log("Deactivating @ mention");
          setAtMentionActive(false);
          setShowGameSearch(false);
          setGameSearchResults([]);
          setFeatureSearchResults([]);
          setAtMentionQuery("");
        }
      } else {
        setAtMentionActive(false);
        setShowGameSearch(false);
        setGameSearchResults([]);
        setFeatureSearchResults([]);
        setAtMentionQuery("");
      }
  };

  const handleGameSelectFromMention = async (game) => {
    if (!inputRef) return;

    const currentInput = input;
    const textBeforeAt = currentInput.substring(0, atMentionPosition);
    const textAfterAt = currentInput.substring(atMentionPosition + 1);

    // Find where the search query ends
    let queryText = atMentionQuery || "";

    if (!queryText) {
      const cursorPos = cursorPosition;
      queryText = currentInput.substring(atMentionPosition + 1, cursorPos).trim();
    }

    let queryEndPos = atMentionPosition + 1;

    if (queryText) {
      if (textAfterAt.startsWith(queryText)) {
        queryEndPos = atMentionPosition + 1 + queryText.length;
      } else {
        const match = textAfterAt.match(/^([^\s\n]+(?:\s+[^\s\n]+)*)/);
        if (match) {
          queryEndPos = atMentionPosition + 1 + match[0].length;
        } else {
          queryEndPos = cursorPosition;
        }
      }
    } else {
      const spaceIndex = textAfterAt.indexOf(' ');
      queryEndPos = spaceIndex !== -1 ? atMentionPosition + 1 + spaceIndex : cursorPosition;
    }

    const textAfterQuery = currentInput.substring(queryEndPos).trimStart();

    // Add game to chips if not already present
    if (!gameChips.find(g => g.id === game.id)) {
      setGameChips([...gameChips, game]);
      // Fetch families for the game
      const families = await fetchGameFamilies(game.id);
      if (families.length > 0) {
        // Filter to only include main series families (those that start with "Game: " or are the game name itself)
        // This excludes generic families like "Digital Implementations: Steam" that are shared by many games
        const gameNameLower = game.name.toLowerCase();
        const mainSeriesFamilies = families.filter(family => {
          const familyLower = family.toLowerCase();
          // Include families that:
          // 1. Start with "Game: " (main series indicator)
          // 2. Match the game name exactly
          // 3. Start with the game name followed by a colon or space
          return familyLower.startsWith("game: ") ||
                 familyLower === gameNameLower ||
                 familyLower.startsWith(gameNameLower + ":") ||
                 familyLower.startsWith(gameNameLower + " ");
        });

        // Log for debugging
        console.log(`[DEBUG] Game: ${game.name}, Total families: ${families.length}, Main series families: ${mainSeriesFamilies.length}`, {
          allFamilies: families,
          mainSeriesFamilies: mainSeriesFamilies
        });

        // Store only main series families for exclusion
        setExcludedFamilies(mainSeriesFamilies.length > 0 ? mainSeriesFamilies : []);
        // Auto-enable exclude same series if main series families exist
        setExcludeSameSeries(mainSeriesFamilies.length > 0);
      }
    }

    // Reset mention state
    setAtMentionActive(false);
    setShowGameSearch(false);
    setGameSearchResults([]);
    setFeatureSearchResults([]);
    setAtMentionQuery("");

    // Replace @ mention with game name in input textbox (don't auto-send)
    const newText = textBeforeAt + game.name + (textAfterQuery ? " " + textAfterQuery : "");
    setInput(newText);

    // Set cursor position after inserted game name
    setTimeout(() => {
      if (inputRef) {
        const newPos = textBeforeAt.length + game.name.length + (textAfterQuery ? 1 : 0);
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

  // Fetch families for a game
  const fetchGameFamilies = async (gameId) => {
    try {
      const res = await httpRequest(`${API_BASE}/games/${gameId}/families`, {
        method: "GET",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        return data.families || [];
      }
    } catch (err) {
      console.error("Error fetching game families:", err);
    }
    return [];
  };

  // eslint-disable-next-line no-unused-vars
  const selectGame = async (game) => {
    if (atMentionActive) {
      handleGameSelectFromMention(game);
    } else {
      // Add game to chips if not already present
      if (!gameChips.find(g => g.id === game.id)) {
        setGameChips([...gameChips, game]);
        // Fetch families for the game
        const families = await fetchGameFamilies(game.id);
        if (families.length > 0) {
          // Filter to only include main series families (those that start with "Game: " or are the game name itself)
          // This excludes generic families like "Digital Implementations: Steam" that are shared by many games
          const gameNameLower = game.name.toLowerCase();
          const mainSeriesFamilies = families.filter(family => {
            const familyLower = family.toLowerCase();
            // Include families that:
            // 1. Start with "Game: " (main series indicator)
            // 2. Match the game name exactly
            // 3. Start with the game name followed by a colon or space
            return familyLower.startsWith("game: ") ||
                   familyLower === gameNameLower ||
                   familyLower.startsWith(gameNameLower + ":") ||
                   familyLower.startsWith(gameNameLower + " ");
          });

          // Log for debugging
          console.log(`[DEBUG] Game: ${game.name}, Total families: ${families.length}, Main series families: ${mainSeriesFamilies.length}`, {
            allFamilies: families,
            mainSeriesFamilies: mainSeriesFamilies
          });

          // Store only main series families for exclusion
          setExcludedFamilies(mainSeriesFamilies.length > 0 ? mainSeriesFamilies : []);
          // Auto-enable exclude same series if main series families exist
          setExcludeSameSeries(mainSeriesFamilies.length > 0);
        }
      }
      setGameSearchResults([]);
      setFeatureSearchResults([]);
      setShowGameSearch(false);
      // Insert game name at cursor position
      insertTextAtCursor(game.name + " ");
    }
  };

  const selectFeature = (feature) => {
    // Replace @ mention with feature name in input
    if (atMentionActive && inputRef) {
      const currentInput = input;
      const textBeforeAt = currentInput.substring(0, atMentionPosition);
      const textAfterAt = currentInput.substring(atMentionPosition + 1);

      let queryText = atMentionQuery || "";
      if (!queryText) {
        const cursorPos = cursorPosition;
        queryText = currentInput.substring(atMentionPosition + 1, cursorPos).trim();
      }

      let queryEndPos = atMentionPosition + 1;
      if (queryText && textAfterAt.startsWith(queryText)) {
        queryEndPos = atMentionPosition + 1 + queryText.length;
      } else {
        const match = textAfterAt.match(/^([^\s\n]+(?:\s+[^\s\n]+)*)/);
        if (match) {
          queryEndPos = atMentionPosition + 1 + match[0].length;
        } else {
          queryEndPos = cursorPosition;
        }
      }

      const textAfterQuery = currentInput.substring(queryEndPos).trimStart();
      const newText = textBeforeAt + feature.name + (textAfterQuery ? " " + textAfterQuery : "");
      setInput(newText);

      // Add feature as required feature chip
      // Use the last message index or 0 if no messages
      // Don't auto-requery when selecting from @ dropdown - let user send manually
      const messageIndex = messages.length > 0 ? messages.length - 1 : 0;
      handleRequireFeature(messageIndex, feature.type, feature.name, false);

      setAtMentionActive(false);
      setShowGameSearch(false);
      setGameSearchResults([]);
      setFeatureSearchResults([]);
      setAtMentionQuery("");

      setTimeout(() => {
        if (inputRef) {
          const newPos = textBeforeAt.length + feature.name.length + (textAfterQuery ? 1 : 0);
          inputRef.setSelectionRange(newPos, newPos);
          setCursorPosition(newPos);
          inputRef.focus();
        }
      }, 0);
    } else {
      // Not in @ mention mode, just add to input
      insertTextAtCursor(feature.name + " ");

      // Add feature as required feature chip
      // Don't auto-requery when selecting from @ dropdown - let user send manually
      const messageIndex = messages.length > 0 ? messages.length - 1 : 0;
      handleRequireFeature(messageIndex, feature.type, feature.name, false);

      setShowGameSearch(false);
      setGameSearchResults([]);
      setFeatureSearchResults([]);
    }
  };

  const removeDoINeedChip = (chipId) => {
    setDoINeedChips(doINeedChips.filter(c => c.id !== chipId));
  };

  const handleDoINeedChipClick = (chip) => {
    // Re-trigger the "Do I need" query
    const query = `Do I need ${chip.name}?`;
    setInput(query);
    // Auto-send the message
    setTimeout(() => {
      sendMessage();
    }, 100);
  };

  const removeGameChip = (gameId) => {
    const game = gameChips.find(g => g.id === gameId);
    if (!game) return;

    // Remove game chip
    const newGameChips = gameChips.filter(g => g.id !== gameId);
    setGameChips(newGameChips);

    // Clear exclude same series if no games left
    if (newGameChips.length === 0) {
      setExcludeSameSeries(false);
      setExcludedFamilies([]);
    }

    // Remove game name from input textbox
    // Handle both comma-separated and space-separated formats
    const gameNameEscaped = game.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    // Remove the game name, handling commas and spaces around it
    let newInput = input
      .replace(new RegExp(`\\s*${gameNameEscaped}\\s*,?\\s*`, 'gi'), ' ') // Remove with comma
      .replace(new RegExp(`\\s*,\\s*${gameNameEscaped}\\s*`, 'gi'), ' ') // Remove with leading comma
      .replace(new RegExp(`\\b${gameNameEscaped}\\b`, 'gi'), '') // Remove standalone
      .replace(/\s+/g, ' ')
      .replace(/^,\s*|,\s*$/g, '') // Remove leading/trailing commas
      .trim();

    // Also remove any "similar to" or "different from" text that would trigger recommend_similar/different
    newInput = newInput
      .replace(/\b(games?\s+)?(similar\s+to|different\s+from)\s+/gi, '')
      .replace(/\s+/g, ' ')
      .trim();

    setInput(newInput);

    // Reset context - when game chip is removed, context should reset to global_search for games matching features
    // Clear any recommend_similar/different context by clearing chips that imply that
    setPromptChips([]);

    // Clear any game-related context from previous queries
    // This ensures that when a feature search is done after removing a game chip,
    // the backend won't use the old game context
    // Note: The context reset happens automatically because selected_game_id will be null
    // and the backend will use global_search when there are features but no base game
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

  // Handle player count selector
  const handlePlayerCountChange = (value) => {
    const numValue = value === '' ? null : parseInt(value);
    setPlayerCount(numValue);

    // Remove old player count from input
    const oldInput = input.replace(/\b\d+\s*players?\b/gi, '').replace(/\s+/g, ' ').trim();

    // Remove old player chips
    setPlayerChips([]);

    if (numValue) {
      // Add new player count to input
      setInput(oldInput + (oldInput ? ' ' : '') + `${numValue} players `);
      setPlayerChips([numValue]);
    } else {
      setInput(oldInput);
    }
  };

  // Handle playtime selector
  const handlePlaytimeChange = (value) => {
    const playtimeOption = PLAYTIME_OPTIONS.find(p => p.value.toString() === value);
    setPlaytime(value === '' ? null : value);

    // Remove old playtime from input
    let oldInput = input;
    PLAYTIME_OPTIONS.forEach(opt => {
      const regex = new RegExp(`\\b${opt.label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
      oldInput = oldInput.replace(regex, '').replace(/\s+/g, ' ').trim();
    });

    // Remove old playtime chips
    setPlaytimeChips([]);

    if (playtimeOption) {
      // Add new playtime to input
      setInput(oldInput + (oldInput ? ' ' : '') + `${playtimeOption.label} `);
      setPlaytimeChips([playtimeOption]);
    } else {
      setInput(oldInput);
    }
  };

  const handleGameChipClick = (game) => {
    // Add game name to input at cursor position
    insertTextAtCursor(game.name + " ");
  };

  const loadThread = async (threadIdToLoad) => {
    try {
      const res = await httpRequest(`${API_BASE}/chat/history/${threadIdToLoad}`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const threadMessages = await res.json();
        const formattedMessages = threadMessages.map((msg) => ({
          role: msg.role,
          text: msg.message,
          results: msg.metadata?.results || [],
          querySpec: msg.metadata?.query_spec || {},
          messageId: msg.id,
          liked: false,
          disliked: false,
          feedbackQuestion: null,
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
    setDoINeedChips([]);
    setUseCollection(false);
  };

  const handleLikeDislike = async (messageIndex, action) => {
    if (!user || !helpfulQuestion) return;

    const message = messages[messageIndex];
    if (!message || message.role !== "assistant") return;

    // Find the option ID for Yes (like) or No (dislike)
    const option = helpfulQuestion.options?.find(opt =>
      (action === "like" && opt.text === "Yes") ||
      (action === "dislike" && opt.text === "No")
    );

    if (!option) {
      console.error("Could not find option for action:", action);
      return;
    }

    // If dislike, show input box first (don't submit yet)
    if (action === "dislike" && option.text === "No") {
      setShowDislikeInput(prev => ({ ...prev, [messageIndex]: true }));
      setMessages((prev) => {
        const updated = [...prev];
        updated[messageIndex] = {
          ...updated[messageIndex],
          disliked: true,
        };
        return updated;
      });
      return; // Don't submit yet, wait for user to optionally add details
    }

    // Update local state immediately
    setMessages((prev) => {
      const updated = [...prev];
      updated[messageIndex] = {
        ...updated[messageIndex],
        liked: action === "like",
        disliked: action === "dislike",
      };
      return updated;
    });

    // Submit feedback
    try {
      const res = await httpRequest(`${API_BASE}/feedback/respond`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: helpfulQuestion.id,
          option_id: option.id,
          response: null,
          additional_details: null,
          context: JSON.stringify({
            message_index: messageIndex,
            message_text: message.text.substring(0, 100), // First 100 chars for context
          }),
          thread_id: threadId || null,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        console.error("Failed to submit like/dislike:", errorData);
        throw new Error(errorData.detail || "Failed to submit feedback");
      }
    } catch (err) {
      console.error("Failed to submit like/dislike:", err);
      // Revert on error
      setMessages((prev) => {
        const updated = [...prev];
        updated[messageIndex] = {
          ...updated[messageIndex],
          liked: false,
          disliked: false,
        };
        return updated;
      });
    }
  };

  const handleDislikeSubmit = async (messageIndex) => {
    if (!user || !helpfulQuestion) return;

    const message = messages[messageIndex];
    if (!message || message.role !== "assistant") return;

    // Find the No option
    const option = helpfulQuestion.options?.find(opt => opt.text === "No");
    if (!option) return;

    const additionalDetails = dislikeDetails[messageIndex] || "";

    // Submit feedback with optional additional details
    try {
      const res = await httpRequest(`${API_BASE}/feedback/respond`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: helpfulQuestion.id,
          option_id: option.id,
          response: null,
          additional_details: additionalDetails.trim() || null,
          context: JSON.stringify({
            message_index: messageIndex,
            message_text: message.text.substring(0, 100),
          }),
          thread_id: threadId || null,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        console.error("Failed to submit dislike feedback:", errorData);
        throw new Error(errorData.detail || "Failed to submit feedback");
      }

      // Hide input after successful submission
      setShowDislikeInput(prev => {
        const newState = { ...prev };
        delete newState[messageIndex];
        return newState;
      });
      setDislikeDetails(prev => {
        const newState = { ...prev };
        delete newState[messageIndex];
        return newState;
      });
    } catch (err) {
      console.error("Failed to submit dislike feedback:", err);
    }
  };

  const handleFeedbackResponse = async (messageIndex, questionId, response) => {
    if (!user) return;

    const message = messages[messageIndex];
    if (!message) return;

    // Find the question to determine its type
    const question = message.feedbackQuestion;
    if (!question) return;

    // Remove feedback question from message after response
    setMessages((prev) => {
      const updated = [...prev];
      updated[messageIndex] = {
        ...updated[messageIndex],
        feedbackQuestion: null,
      };
      return updated;
    });

    // Handle different response types
    let optionId = null;
    let responseText = null;

    if (question.question_type === "single_select") {
      // Single select: response is an option object with id
      if (typeof response === 'object' && response !== null) {
        if (response.id !== undefined && response.id !== null) {
          optionId = response.id;
        } else {
          console.error("Single select response missing id:", response);
        }
      } else if (Array.isArray(response) && response.length > 0 && response[0]?.id) {
        // Handle array case (shouldn't happen for single_select, but be safe)
        optionId = response[0].id;
      } else {
        console.error("Invalid single_select response format:", response);
      }
    } else if (question.question_type === "multi_select") {
      // Multi select: response is an array of option objects
      // Store as JSON array of option IDs
      if (Array.isArray(response) && response.length > 0) {
        const optionIds = response.map(r => r.id).filter(id => id != null);
        responseText = JSON.stringify(optionIds);
      }
    } else {
      // Text question: response is a string
      responseText = typeof response === 'object' ? response.text || JSON.stringify(response) : response;
    }

    // Submit feedback
    try {
      const requestBody = {
        question_id: questionId !== null && questionId !== undefined ? questionId : null,
        option_id: optionId !== null && optionId !== undefined ? optionId : null,
        response: responseText !== null && responseText !== undefined ? responseText : null,
        context: JSON.stringify({
          message_index: messageIndex,
          message_text: message.text.substring(0, 100),
        }),
        thread_id: threadId !== null && threadId !== undefined ? threadId : null,
      };

      console.log("Submitting feedback:", {
        question_type: question.question_type,
        questionId,
        optionId,
        responseText,
        originalResponse: response,
        requestBody
      });

      const res = await httpRequest(`${API_BASE}/feedback/respond`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        console.error("Failed to submit feedback:", errorData);
        throw new Error(errorData.detail || "Failed to submit feedback");
      }

      const result = await res.json();
      console.log("Feedback submitted successfully:", result);
    } catch (err) {
      console.error("Failed to submit feedback:", err);
      alert(err.message || "Failed to submit feedback. Please try again.");
    }
  };

  const handleRequireFeature = async (messageIndex, featureType, featureValue, autoRequery = true) => {
    setRequiredFeatures((prev) => {
      const newRequired = { ...prev };
      if (!newRequired[messageIndex]) {
        newRequired[messageIndex] = {};
      }
      if (!newRequired[messageIndex][featureType]) {
        newRequired[messageIndex][featureType] = new Set();
      }
      // Add the feature to required set
      newRequired[messageIndex][featureType].add(featureValue);
      return newRequired;
    });

    // Update active required features for display
    setActiveRequiredFeatures((prev) => {
      const key = `${featureType}:${featureValue}`;
      if (!prev.find(f => f.key === key)) {
        return [...prev, { type: featureType, value: featureValue, key, messageIndex }];
      }
      return prev;
    });

    // Re-query with required feature (only if autoRequery is true)
    if (!autoRequery) {
      return;
    }

    const message = messages[messageIndex];
    if (message && message.querySpec) {
      // Find the original user message that triggered this response
      // Look backwards from the assistant message to find the user message
      let originalUserMessage = null;
      for (let i = messageIndex - 1; i >= 0; i--) {
        if (messages[i].role === "user") {
          originalUserMessage = messages[i].text;
          break;
        }
      }

      if (originalUserMessage) {
        // Get current required features - use functional update to get latest state
        let requiredArray = {};
        setRequiredFeatures((prev) => {
          const newRequired = prev;

          // Build required feature values object - aggregate ALL required features from ALL messages
          const required = {};
          Object.keys(newRequired).forEach(msgIdx => {
            Object.keys(newRequired[msgIdx]).forEach(ft => {
              if (!required[ft]) {
                required[ft] = new Set();
              }
              newRequired[msgIdx][ft].forEach(val => required[ft].add(val));
            });
          });

          // Convert Sets to Arrays
          Object.keys(required).forEach(ft => {
            requiredArray[ft] = Array.from(required[ft]);
          });

          return newRequired; // Return unchanged state
        });

        // Re-send the query with required features in context (async operation outside setState)
        try {
          const context = {
            last_game_id: gameChips.length > 0 ? gameChips[0].id : null,
            useCollection: useCollection,
            selected_game_id: gameChips.length > 0 ? gameChips[0].id : null,
            player_chips: playerChips,
            playtime_chips: playtimeChips.map(c => c.value),
            required_feature_values: requiredArray, // Pass required features in context
          };

          const requestBody = {
            user_id: user?.id?.toString() || null,
            message: originalUserMessage,
            context,
            thread_id: threadId,
            selected_game_id: gameChips.length > 0 ? gameChips[0].id : null,
          };

          const res = await httpRequest(`${API_BASE}/chat`, {
            method: "POST",
            headers: {
              ...authService.getAuthHeaders(),
              "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
          });
          const data = await res.json();
          // Process response data
          if (data) {

            // Build user message text showing the context
            let userMessageText = originalUserMessage;
            const contextParts = [];

            // Add game chips
            if (gameChips.length > 0) {
              contextParts.push(`Game: ${gameChips.map(c => c.name).join(", ")}`);
            }

            // Add player chips
            if (playerChips.length > 0) {
              const playerText = playerChips.map(c => `${c.min}-${c.max} players`).join(", ");
              contextParts.push(playerText);
            }

            // Add playtime chips
            if (playtimeChips.length > 0) {
              const playtimeText = playtimeChips.map(c => c.label).join(", ");
              contextParts.push(`Playtime: ${playtimeText}`);
            }

            // Add required features
            if (Object.keys(requiredArray).length > 0) {
              const featureParts = [];
              Object.keys(requiredArray).forEach(ft => {
                const featureTypeLabel = ft === "mechanics" ? "Mechanics" :
                                        ft === "categories" ? "Categories" :
                                        ft === "themes" ? "Themes" :
                                        ft === "designers" ? "Designers" :
                                        ft === "publishers" ? "Publishers" : ft;
                featureParts.push(`${featureTypeLabel}: ${requiredArray[ft].join(", ")}`);
              });
              contextParts.push(`Required: ${featureParts.join("; ")}`);
            }

            if (contextParts.length > 0) {
              userMessageText = `${originalUserMessage} [${contextParts.join(" | ")}]`;
            }

            // Add collection context if applicable
            if (useCollection) {
              userMessageText += " in my collection";
            }

            // Create new user message showing the context
            const newUserMessage = {
              role: "user",
              text: userMessageText,
              messageId: Date.now(),
            };

            // Create new assistant message with updated results (instead of overwriting)
            setMessages((prev) => {
              const updated = [...prev];

              // Add the new user message
              updated.push(newUserMessage);

              // Handle A/B test responses
              if (data.ab_responses && data.ab_responses.length > 0) {
                const abResp = data.ab_responses[0];
                const newAssistantMessage = {
                  role: "assistant",
                  text: data.reply_text,
                  querySpec: data.query_spec || {},
                  messageId: Date.now() + 1,
                  liked: false,
                  disliked: false,
                  abTest: {
                    config_key: abResp.config_key,
                    config_name: abResp.config_name,
                    response_a: {
                      label: abResp.response_a.label,
                      results: abResp.response_a.results || [],
                      config_value: abResp.response_a.config_value
                    },
                    response_b: {
                      label: abResp.response_b.label,
                      results: abResp.response_b.results || [],
                      config_value: abResp.response_b.config_value
                    },
                    question_id: abResp.question_id,
                    question_text: abResp.question_text || `Which response do you prefer for ${abResp.config_name}?`,
                    question_type: "single_select",
                    options: abResp.options || [
                      { id: 1, text: abResp.response_a.label },
                      { id: 2, text: abResp.response_b.label }
                    ]
                  },
                  results: [] // Clear regular results when we have A/B test
                };
                updated.push(newAssistantMessage);
              } else {
                // Regular single response
                const newAssistantMessage = {
                  role: "assistant",
                  text: data.reply_text,
                  results: data.results || [],
                  querySpec: data.query_spec || {},
                  messageId: Date.now() + 1,
                  liked: false,
                  disliked: false,
                  feedbackQuestion: null,
                  abTest: null
                };
                updated.push(newAssistantMessage);
              }

              return updated;
            });
          }
        } catch (err) {
          console.error("Failed to re-query:", err);
          alert("Failed to update results. Please try again.");
        }
      }
    }
  };

  const removeRequiredFeature = (key) => {
    setActiveRequiredFeatures((prev) => {
      const feature = prev.find(f => f.key === key);
      if (!feature) return prev;

      // Remove from requiredFeatures state
      setRequiredFeatures((prevReq) => {
        const newRequired = { ...prevReq };
        if (newRequired[feature.messageIndex] && newRequired[feature.messageIndex][feature.type]) {
          newRequired[feature.messageIndex][feature.type].delete(feature.value);
          if (newRequired[feature.messageIndex][feature.type].size === 0) {
            delete newRequired[feature.messageIndex][feature.type];
          }
        }
        return newRequired;
      });

      return prev.filter(f => f.key !== key);
    });
  };

  const sendMessage = async (messageTextOverride = null) => {
    // Prevent duplicate sends - if already processing, don't send again
    if (isProcessing) return;

    // Check message limit for anonymous users
    if (!user) {
      if (hasExceededLimit(5)) {
        setMessageLimitError(`You've reached the daily limit of 5 messages. Please log in to continue chatting!`);
        return;
      }
    }

    // Clear any previous message limit error
    setMessageLimitError(null);

    // Use override text if provided, otherwise use input
    // Ensure messageText is always a string (not an event object)
    let messageText = messageTextOverride || input.trim() || (activeRequiredFeatures.length > 0
      ? `Find games with ${activeRequiredFeatures.map(f => f.value).join(", ")}`
      : "");
    // Convert to string if it's not already (safety check)
    if (typeof messageText !== 'string') {
      console.error('messageText is not a string:', messageText);
      messageText = String(messageText);
    }
    if (!messageText) return;

    // Check if this is a response to a follow-up prompt (theme/mechanics preference)
    // These should always trigger similarity search, not game detail view
    const isPromptResponse = (() => {
      if (messages.length === 0) return false;
      const lastAssistantMsg = [...messages].reverse().find(m => m.role === "assistant");
      if (!lastAssistantMsg) return false;
      const lastText = lastAssistantMsg.text || "";
      const hasFollowupPrompt = lastText.includes("Do you prefer") ||
                               lastText.includes("prefer 1") ||
                               lastText.includes("prefer 2");
      const currentText = messageText.toLowerCase().trim();
      const isPromptResponse = hasFollowupPrompt && (
        currentText === "1" ||
        currentText === "2" ||
        currentText.includes("theme") ||
        currentText.includes("mechanics")
      );
      return isPromptResponse;
    })();

    // Check if this is a "game detail only" query (only game chip, no other filters)
    // Exclude if there are prompt chips (like "Games similar to") or any other text/context
    // Also exclude if this is a response to a follow-up prompt
    // Check messageText (not input) since sendMessage can be called with override text
    const messageTextLower = messageText.toLowerCase();
    const hasSearchKeywords = messageTextLower.match(/\b(similar|different|compare|like|games|find|search|recommend|with similar theme|with similar mechanics)\b/);

    const hasOtherContext = playerChips.length > 0 ||
                            playtimeChips.length > 0 ||
                            activeRequiredFeatures.length > 0 ||
                            useCollection ||
                            chips.length > 0 ||
                            promptChips.length > 0 ||
                            isPromptResponse ||
                            hasSearchKeywords; // Has search-related keywords in the message text

    const isGameDetailOnly = gameChips.length === 1 && !hasOtherContext;

    const messageId = Date.now();
    const userMsg = {
      role: "user",
      text: messageText,
      messageId: messageId,
      status: "sending"
    };
    setMessages((prev) => [...prev, userMsg]);

    // If this is a game detail only query, fetch game details instead of doing a search
    // Note: This does NOT count against message limit (only search queries do)
    if (isGameDetailOnly) {
      const gameId = gameChips[0].id;

      // Update message status to "sent"
      setMessages((prev) => {
        return prev.map(msg =>
          msg.messageId === messageId
            ? { ...msg, status: "sent" }
            : msg
        );
      });

      setIsProcessing(true);
      setShowProcessingIndicator(false);

      try {
        const detailsRes = await httpRequest(`${API_BASE}/games/${gameId}/details`, {
          method: "GET",
          headers: authService.getAuthHeaders(),
        });

        if (detailsRes.ok) {
          const gameDetails = await detailsRes.json();

          // Create assistant message with game details
          // Also include follow-up prompt to ask about theme/mechanics preference
          const botMsg = {
            role: "assistant",
            text: `Here's information about ${gameDetails.name}:`,
            gameDetails: gameDetails,
            messageId: Date.now(),
            liked: false,
            disliked: false,
            followupPrompt: "Do you prefer 1) the theme, or 2) the mechanics?", // Add follow-up prompt for game details too
          };

          setMessages((prev) => [...prev, botMsg]);
          setIsProcessing(false);
          if (processingTimeout) {
            clearTimeout(processingTimeout);
            setProcessingTimeout(null);
          }
          setShowProcessingIndicator(false);
          return; // Exit early, don't proceed with normal chat flow
        } else {
          throw new Error("Failed to fetch game details");
        }
      } catch (err) {
        console.error("Failed to fetch game details:", err);
        // Show error message
        const errorMsg = {
          role: "assistant",
          text: `Sorry, I couldn't fetch details for that game. Please try again.`,
          messageId: Date.now(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        setIsProcessing(false);
        if (processingTimeout) {
          clearTimeout(processingTimeout);
          setProcessingTimeout(null);
        }
        setShowProcessingIndicator(false);
        return; // Exit early
      }
    }

    // Build context - include all feature information for feature-only searches
    const requiredFeatureValues = activeRequiredFeatures.length > 0 ?
      activeRequiredFeatures.reduce((acc, f) => {
        if (!acc[f.type]) acc[f.type] = [];
        acc[f.type].push(f.value);
        return acc;
      }, {}) : undefined;

    // Build excluded feature values
    const excludedFeatureValues = {};
    if (excludeSameSeries && excludedFamilies.length > 0) {
      excludedFeatureValues.families = excludedFamilies;
    }
    if (excludeImplementationCategories) {
      // Implementation/publishing categories to exclude
      excludedFeatureValues.categories = [
        "Digital Implementation",
        "Crowdfunding",
        "Digital Game",
        "App Implementation",
        "Video Game Theme",
        "Software"
      ];
    }
    const finalExcludedFeatureValues = Object.keys(excludedFeatureValues).length > 0 ? excludedFeatureValues : undefined;

    const context = {
      last_game_id: gameChips.length > 0 ? gameChips[0].id : null,
      useCollection: useCollection,
      selected_game_id: gameChips.length > 0 ? gameChips[0].id : null,
      player_chips: playerChips,
      playtime_chips: playtimeChips.map(c => c.value),
      // Include required features from active required features
      required_feature_values: requiredFeatureValues,
      // Include excluded feature values for exclude same series
      excluded_feature_values: finalExcludedFeatureValues,
    };

    // If useCollection is checked, explicitly set scope in message
    let finalMessageText = messageText;
    if (useCollection && !finalMessageText.toLowerCase().includes("in my collection") && !finalMessageText.toLowerCase().includes("my collection")) {
      finalMessageText = finalMessageText + " in my collection";
    }

    // Check if this is a response to a prompt (theme/mechanics preference, etc.)
    // Don't count responses to prompts against message limit
    const isResponseToPrompt = (() => {
      if (messages.length === 0) return false;

      // Get the last assistant message
      const lastAssistantMsg = [...messages].reverse().find(m => m.role === "assistant");
      if (!lastAssistantMsg) return false;

      const lastText = lastAssistantMsg.text || "";
      const currentText = messageText.toLowerCase().trim();

      // Check if last message contains a follow-up prompt
      const hasFollowupPrompt = lastText.includes("Do you prefer") ||
                                 lastText.includes("prefer 1") ||
                                 lastText.includes("prefer 2");

      // Check if current message is a response to that prompt
      const isPromptResponse = hasFollowupPrompt && (
        currentText === "1" ||
        currentText === "2" ||
        currentText.includes("theme") ||
        currentText.includes("mechanics") ||
        currentText.includes("the theme") ||
        currentText.includes("the mechanics")
      );

      return isPromptResponse;
    })();

    // Increment message count for anonymous users (only for search queries, not game detail views or prompt responses)
    // Game detail queries are handled above and don't reach here
    // Prompt responses should not count against limit
    if (!user && !isResponseToPrompt) {
      incrementMessageCount();
    }

    // Set processing state and timeout indicator
    setIsProcessing(true);
    setShowProcessingIndicator(false);
    const timeoutId = setTimeout(() => {
      // Show processing indicator after 5 seconds
      setShowProcessingIndicator(true);
    }, 5000);
    setProcessingTimeout(timeoutId);

    try {
      const res = await httpRequest(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user?.id?.toString() || null,
          message: finalMessageText,
          context: {
            ...context,
            // Pass theme/mechanics preference if this is a response to a prompt
            theme_preference: isResponseToPrompt && (messageText.toLowerCase().includes("theme") || messageText.trim() === "1") ? "theme" : undefined,
            mechanics_preference: isResponseToPrompt && (messageText.toLowerCase().includes("mechanics") || messageText.trim() === "2") ? "mechanics" : undefined,
          },
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

      // Update message status to "sent"
      setMessages((prev) => {
        return prev.map(msg =>
          msg.messageId === messageId
            ? { ...msg, status: "sent" }
            : msg
        );
      });

      // Handle A/B test responses
      if (data.ab_responses && data.ab_responses.length > 0) {
        // Create a single A/B test message with parallel columns
        const abResp = data.ab_responses[0]; // For now, handle first A/B test
        const botMsg = {
          role: "assistant",
          text: data.reply_text,
          querySpec: data.query_spec || {},
          messageId: Date.now(),
          liked: false,
          disliked: false,
          abTest: {
            config_key: abResp.config_key,
            config_name: abResp.config_name,
            response_a: {
              label: abResp.response_a.label,
              results: abResp.response_a.results || [],
              config_value: abResp.response_a.config_value
            },
            response_b: {
              label: abResp.response_b.label,
              results: abResp.response_b.results || [],
              config_value: abResp.response_b.config_value
            },
            question_id: abResp.question_id,
            question_text: abResp.question_text || `Which response do you prefer for ${abResp.config_name}?`,
            question_type: "single_select",
            options: abResp.options || [
              { id: 1, text: abResp.response_a.label },
              { id: 2, text: abResp.response_b.label }
            ]
          }
        };

        setMessages((prev) => [...prev, botMsg]);
      } else {
        // Regular single response
        const botMsg = {
          role: "assistant",
          text: data.reply_text,
          results: data.results || [],
          querySpec: data.query_spec || {},
          messageId: Date.now(), // Temporary ID for tracking
          liked: false,
          disliked: false,
          feedbackQuestion: null,
          followupPrompt: data.followup_prompt || null, // Store follow-up prompt
        };

        setMessages((prev) => [...prev, botMsg]);
      }

      // Request feedback question after response and attach to message
      if (user) {
        try {
          const feedbackRes = await httpRequest(`${API_BASE}/feedback/questions/random`, {
            method: "GET",
            headers: authService.getAuthHeaders(),
          });
          if (feedbackRes.ok) {
            const feedbackQuestion = await feedbackRes.json();
            if (feedbackQuestion) {
              // Update the last message with the feedback question
              setMessages((prev) => {
                const updated = [...prev];
                if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
                  updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    feedbackQuestion: feedbackQuestion,
                  };
                }
                return updated;
              });
            }
          }
        } catch (err) {
          console.error("Failed to get feedback question:", err);
        }
      }
      // After response is processed, automatically add game chips and required features to search text box
      // Only populate if input is currently empty or matches exactly what we would set
      // This prevents overwriting user input or re-adding removed game names
      const currentInputTrimmed = input.trim();
      const expectedText = (() => {
        const parts = [];
        if (gameChips.length > 0) {
          parts.push(...gameChips.map(g => g.name));
        }
        if (activeRequiredFeatures.length > 0) {
          parts.push(...activeRequiredFeatures.map(f => f.value));
        }
        return parts.join(", ");
      })();

      // Only update input if it's empty or matches exactly what we would set
      // This prevents re-adding removed game names
      if (!currentInputTrimmed || currentInputTrimmed === expectedText) {
        setInput(expectedText);
      }
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

      // Add "Do I need" chip if this was a collection_recommendation query
      if (data.query_spec?.intent === "collection_recommendation" && data.query_spec?.base_game_id) {
        // Get game name from game chips or extract from user message
        let gameName = null;
        let gameId = data.query_spec.base_game_id;

        // Try to find game name from game chips
        const gameChip = gameChips.find(g => g.id === gameId);
        if (gameChip) {
          gameName = gameChip.name;
        } else {
          // Try to extract from the last user message
          const lastUserMessage = messages.find(m => m.role === "user");
          if (lastUserMessage) {
            // Extract game name from "Do I need X?" query
            const match = lastUserMessage.text.match(/do i need (.+?)\??$/i);
            if (match) {
              gameName = match[1].trim();
            }
          }
        }

        if (gameName && !doINeedChips.find(c => c.game_id === gameId)) {
          setDoINeedChips([...doINeedChips, { id: Date.now(), name: gameName, game_id: gameId }]);
        }
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      // Update message status to "error"
      setMessages((prev) => {
        return prev.map(msg =>
          msg.messageId === messageId
            ? { ...msg, status: "error" }
            : msg
        );
      });
      alert(err.message || "Failed to send message. Please try again.");
    } finally {
      // Clear processing state
      setIsProcessing(false);
      setShowProcessingIndicator(false);
      if (processingTimeout) {
        clearTimeout(processingTimeout);
        setProcessingTimeout(null);
      }
    }
  };

  // Handle welcome message options
  const handleWelcomeOption = useCallback((option) => {
    if (option === 'game_in_mind') {
      setUserJourneyState('game_in_mind');
      setShowWelcomeMessage(false);
      // Add a message prompting user to search for a game
      const welcomeMsg = {
        role: "assistant",
        text: "Great! Please search for a game using @ in the text box below. Type @ and start typing the game name.",
        messageId: Date.now(),
      };
      setMessages([welcomeMsg]);
    } else if (option === 'exploring') {
      setUserJourneyState('exploring');
      setShowWelcomeMessage(false);
      // Start exploring mode - user can search freely
      const welcomeMsg = {
        role: "assistant",
        text: "Let's explore! You can search for games by typing in the box below, or use @ to search for specific games, mechanics, or categories.",
        messageId: Date.now(),
      };
      setMessages([welcomeMsg]);
    }
  }, []);

  // Define onAddToSearch callback before return
  const onAddToSearchCallback = useCallback((text, type, gameId) => {
    // If it's a game, add to gameChips using functional update to avoid stale closure
    if (type === 'game' && gameId) {
      setGameChips((currentChips) => {
        // Check if game already in chips
        if (!currentChips.find(g => g.id === gameId)) {
          return [...currentChips, { id: gameId, name: text }];
        }
        return currentChips;
      });
    }

    // Add text to input, prefixed with @ if not already there
    const searchText = text.startsWith('@') ? text : `@${text}`;
    setInput((currentInput) => {
      const trimmed = currentInput.trim();
      return trimmed ? `${trimmed} ${searchText}` : searchText;
    });

    // Focus input and trigger search
    if (inputRef) {
      inputRef.focus();
      const cursorPos = inputRef.selectionStart || 0;
      setCursorPosition(cursorPos);
      handleGameSearch(text);
    }
  }, [inputRef, handleGameSearch]);

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
        <>
          {showHistory && (
            <div
              className="history-backdrop"
              onClick={() => setShowHistory(false)}
              aria-label="Close history"
            />
          )}
          <div className={`chat-history-sidebar ${showHistory ? "visible" : ""}`}>
            <div className="history-header">
              <h3>Chat History</h3>
              <button
                onClick={startNewChat}
                className="new-chat-button"
                aria-label="Start new chat"
              >
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
                    onClick={() => {
                      loadThread(thread.id);
                      // Close history on mobile after selection
                      if (window.innerWidth <= 768) {
                        setShowHistory(false);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        loadThread(thread.id);
                        if (window.innerWidth <= 768) {
                          setShowHistory(false);
                        }
                      }
                    }}
                    aria-label={`Load chat: ${thread.title}`}
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
        </>
      )}

      {featuresEditorGame && (
        <GameFeaturesEditor
          gameId={featuresEditorGame.id}
          gameName={featuresEditorGame.name}
          onClose={() => setFeaturesEditorGame(null)}
        />
      )}
      {scoringPadGame && (
        <ScoringPad
          game={scoringPadGame}
          onClose={() => setScoringPadGame(null)}
        />
      )}
      <div className="pista-chat">
        {user && (
          <div className="chat-header">
            <button
              className="toggle-history"
              onClick={() => setShowHistory(!showHistory)}
              aria-label={showHistory ? "Hide chat history" : "Show chat history"}
              aria-expanded={showHistory}
            >
              {showHistory ? "◀" : "▶"} History
            </button>
          </div>
        )}
        <div
          className="chat-window"
          role="log"
          aria-live="polite"
          aria-label="Chat messages"
          tabIndex={0}
        >
          <MessageList
            messages={messages}
            setMessages={setMessages}
            user={user}
            onGameClick={(game) => {
              // Only allow features editor for admin users
              const isRightClick = window.event && (window.event.button === 2 || window.event.ctrlKey);
              if (isRightClick && user && user.is_admin) {
                setFeaturesEditorGame({ id: game.game_id, name: game.name });
              } else {
                setMarketplaceGame({ id: game.game_id, name: game.name });
              }
            }}
            onAddToSearch={onAddToSearchCallback}
            onLikeDislike={handleLikeDislike}
            showWelcomeMessage={showWelcomeMessage}
            handleWelcomeOption={handleWelcomeOption}
            onFeedbackResponse={handleFeedbackResponse}
            helpfulQuestion={helpfulQuestion}
            showDislikeInput={showDislikeInput}
            dislikeDetails={dislikeDetails}
            setDislikeDetails={setDislikeDetails}
            setShowDislikeInput={setShowDislikeInput}
            handleDislikeSubmit={handleDislikeSubmit}
            onRequireFeature={(messageIndex, featureType, featureValue) => {
              // Use functional update to get latest input state
              setInput((currentInput) => {
                const trimmed = (currentInput || "").trim();
                const newInput = trimmed + (trimmed ? ", " : "") + featureValue;

                // Add feature as required feature chip (without auto-requery)
                handleRequireFeature(messageIndex, featureType, featureValue, false);

                return newInput;
              });
            }}
            onFollowupSelect={(preferenceText) => {
              // Ensure preferenceText is a string (not an event object)
              if (typeof preferenceText !== 'string') {
                console.error('onFollowupSelect received non-string:', preferenceText);
                return;
              }

              // When selecting theme/mechanics preference, preserve the game name in the input
              // Get the game name from chips if available, or from the last message's gameDetails
              let gameName = '';
              if (gameChips.length > 0) {
                gameName = gameChips[0].name;
              } else {
                // Try to get game name from the last assistant message's gameDetails
                const lastAssistantMsg = [...messages].reverse().find(m => m.role === "assistant" && m.gameDetails);
                if (lastAssistantMsg && lastAssistantMsg.gameDetails) {
                  gameName = lastAssistantMsg.gameDetails.name;
                  // Also add the game to chips so it's available for the search
                  if (lastAssistantMsg.gameDetails.id) {
                    setGameChips([{ id: lastAssistantMsg.gameDetails.id, name: gameName }]);
                  }
                }
              }

              // Set input to include game name + preference text that makes it clear what the user wants
              // preferenceText is "1" for theme or "2" for mechanics
              const preferenceLabel = preferenceText === "1" ? "with similar theme" : "with similar mechanics";
              const newInput = gameName ? `games similar to ${gameName} ${preferenceLabel}` : preferenceText;

              // Ensure newInput is a string
              if (typeof newInput !== 'string') {
                console.error('newInput is not a string:', newInput);
                return;
              }

              // Update input state for UI
              setInput(newInput);

              // Send message immediately with the new text (don't wait for state update)
              sendMessage(newInput);
            }}
          />
        </div>

        {/* Filters Overlay */}
        {showFiltersOverlay && (
          <div className="filters-overlay" role="dialog" aria-modal="true" aria-labelledby="filters-overlay-title">
            <div className="filters-overlay-content">
              <div className="filters-overlay-header">
                <h3 id="filters-overlay-title">Filters & Options</h3>
                <button
                  onClick={() => setShowFiltersOverlay(false)}
                  className="filters-overlay-close"
                  aria-label="Close filters overlay"
                >
                  ×
                </button>
              </div>
              <div className="filters-overlay-body">
                {/* Active chips display */}
                <div className="active-chips-section">
                  <h4>Active Filters:</h4>
                  <div className="active-chips">
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
                          aria-label={`Remove ${prompt} filter`}
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
                          aria-label={`Remove ${game.name} filter`}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                    {doINeedChips.map((chip) => (
                      <div className="chip game-chip" key={chip.id}>
                        <span
                          onClick={() => handleDoINeedChipClick(chip)}
                          style={{ cursor: "pointer", flex: 1 }}
                          title="Click to ask again"
                        >
                          ❓ Do I need {chip.name}?
                        </span>
                        <button
                          onClick={() => removeDoINeedChip(chip.id)}
                          className="chip-remove"
                          title="Remove"
                          aria-label={`Remove ${chip.name} filter`}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Common prompts */}
                <div className="common-prompts-section">
                  <h4>Quick Prompts:</h4>
                  <div className="common-prompts">
                    {COMMON_PROMPTS.filter(p => !promptChips.includes(p)).map((prompt) => (
                      <button
                        key={prompt}
                        className="chip prompt-button"
                        onClick={() => {
                          addPromptChip(prompt);
                          setShowFiltersOverlay(false);
                        }}
                        title="Add prompt"
                        aria-label={`Add ${prompt} prompt`}
                      >
                        + {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="filters-overlay-backdrop" onClick={() => setShowFiltersOverlay(false)} aria-label="Close overlay"></div>
          </div>
        )}

        <div className="chat-input-container" style={{ position: "relative" }}>
          {/* Message limit warning for anonymous users */}
          {!user && messageLimitError && (
            <div className="message-limit-error">
              {messageLimitError}
              <Link to="/login" className="message-limit-link">
                Log in to continue
              </Link>
            </div>
          )}
          {!user && !messageLimitError && (
            <div className="message-limit-info">
              {getRemainingMessages(5)} messages remaining today. <Link to="/login" className="message-limit-link">Log in</Link> for unlimited messages.
            </div>
          )}
          {/* Processing indicator - only show after 5 seconds */}
          {isProcessing && showProcessingIndicator && (
            <div className="processing-indicator">
              Processing request...
            </div>
          )}

          <div className="chat-input-wrapper">
              {activeRequiredFeatures.length > 0 && (
                <div className="required-features-bar">
                  <span className="required-features-label">Required features:</span>
                  <div className="required-features-list">
                    {activeRequiredFeatures.map((feature) => (
                      <button
                        key={feature.key}
                        className="required-feature-tag"
                        onClick={() => removeRequiredFeature(feature.key)}
                        title="Click to remove"
                        aria-label={`Remove ${feature.value} requirement`}
                      >
                        {feature.type === "mechanics" && "⚙️ "}
                        {feature.type === "categories" && "🏷️ "}
                        {feature.type === "designers" && "👤 "}
                        {feature.type === "families" && "👨‍👩‍👧‍👦 "}
                        {feature.value}
                        <span className="remove-icon">×</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="chat-input-box">
                <div className="chat-input-inner">
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
                      if (e.key === "Enter" && !e.shiftKey && !atMentionActive && !isProcessing) {
                        e.preventDefault();
                        sendMessage();
                      } else if (e.key === "Escape") {
                        setAtMentionActive(false);
                        setShowGameSearch(false);
                      }
                    }}
                    placeholder={gameChips.length > 0 ? `Ask about games similar to ${gameChips[0].name}...` : "Type @ to search for games, mechanics, categories, designers, or publishers"}
                    disabled={isProcessing}
                    className="chat-input-field"
                    aria-label="Chat input"
                    aria-describedby="chat-input-help"
                    autoComplete="off"
                    spellCheck="true"
                  />
                  <span id="chat-input-help" className="sr-only">
                    Type your message here. Use @ to search for games and features. Press Enter to send.
                  </span>

                  <div className="chat-input-actions">
                    <button
                      onClick={async () => {
                        const lastGameId = gameChips.length > 0 ? gameChips[0].id : null;
                        const currentContext = input.trim() || null;

                        if (!lastGameId) {
                          alert("Please select a game first using @ mention in the search box");
                          if (inputRef) {
                            inputRef.focus();
                          }
                          return;
                        }

                        try {
                          const res = await httpRequest(`${API_BASE}/image/generate`, {
                            method: "POST",
                            headers: {
                              ...authService.getAuthHeaders(),
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                              game_id: lastGameId,
                              context: currentContext,
                            }),
                          });

                          if (res.ok) {
                            const data = await res.json();
                            const fakeMsg = {
                              role: "assistant",
                              text: data.message,
                              messageId: Date.now(),
                              isFakeDoor: true,
                            };
                            setMessages((prev) => [...prev, fakeMsg]);
                          } else {
                            alert("Failed to process request");
                          }
                        } catch (err) {
                          console.error("Image upload fake-door failed:", err);
                          alert("Failed to process request");
                        }
                      }}
                      className={`chat-action-btn ${gameChips.length > 0 ? 'enabled' : 'disabled'}`}
                      title={gameChips.length > 0 ? "Upload image (coming soon)" : "Select a game first using @ mention"}
                      disabled={gameChips.length === 0}
                      aria-label="Upload image"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21 15 16 10 5 21"/>
                      </svg>
                    </button>

                    <button
                      onClick={async () => {
                        const lastGameId = gameChips.length > 0 ? gameChips[0].id : null;
                        const currentContext = input.trim() || null;

                        if (!lastGameId) {
                          alert("Please select a game first to explain its rules");
                          return;
                        }

                        try {
                          const res = await httpRequest(`${API_BASE}/rules/explain`, {
                            method: "POST",
                            headers: {
                              ...authService.getAuthHeaders(),
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                              game_id: lastGameId,
                              context: currentContext,
                            }),
                          });

                          if (res.ok) {
                            const data = await res.json();
                            const fakeMsg = {
                              role: "assistant",
                              text: data.message,
                              messageId: Date.now(),
                              isFakeDoor: true,
                            };
                            setMessages((prev) => [...prev, fakeMsg]);
                          } else {
                            alert("Failed to request rules explanation");
                          }
                        } catch (err) {
                          console.error("Rules explainer failed:", err);
                          alert("Failed to request rules explanation");
                        }
                      }}
                      className={`chat-action-btn ${gameChips.length > 0 ? 'enabled' : 'disabled'}`}
                      title={gameChips.length > 0 ? "Explain game rules" : "Select a game first using @ mention"}
                      disabled={gameChips.length === 0}
                      aria-label="Explain game rules"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                      </svg>
                    </button>

                    <button
                      onClick={async () => {
                        const lastGameId = gameChips.length > 0 ? gameChips[0].id : null;
                        const currentContext = input.trim() || null;

                        if (!lastGameId) {
                          alert("Please select a game first to open scoring pad");
                          return;
                        }

                        try {
                          const res = await httpRequest(`${API_BASE}/scoring/pad`, {
                            method: "POST",
                            headers: {
                              ...authService.getAuthHeaders(),
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({
                              game_id: lastGameId,
                              context: currentContext,
                            }),
                          });

                          const data = await res.json();

                          if (data.success && data.fake_door) {
                            alert(data.message);
                          } else if (data.exists && data.mechanism) {
                            setScoringPadGame({ id: lastGameId, name: gameChips[0].name, mechanism: data.mechanism });
                          } else {
                            alert("Scoring mechanism not available for this game yet.");
                          }
                        } catch (err) {
                          console.error("Scoring pad failed:", err);
                          alert("Failed to open scoring pad");
                        }
                      }}
                      className={`chat-action-btn ${gameChips.length > 0 ? 'enabled' : 'disabled'}`}
                      title={gameChips.length > 0 ? "End-game scoring pad" : "Select a game first using @ mention"}
                      disabled={gameChips.length === 0}
                      aria-label="Open scoring pad"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                      </svg>
                    </button>

                    <button
                      onClick={sendMessage}
                      disabled={isProcessing || (!input.trim() && activeRequiredFeatures.length === 0)}
                      className={`chat-send-btn ${(isProcessing || input.trim() || activeRequiredFeatures.length > 0) ? 'enabled' : 'disabled'}`}
                      title={isProcessing ? "Processing request..." : "Send message"}
                      aria-label="Send message"
                    >
                      {isProcessing ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10"/>
                          <path d="M12 6v6l4 2"/>
                        </svg>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="22" y1="2" x2="11" y2="13"/>
                          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Search dropdown for @ mentions - shows both games and features */}
                {atMentionActive && showGameSearch && (gameSearchResults.length > 0 || featureSearchResults.length > 0) && (
                  <div className="game-search-dropdown" style={{ position: "absolute", bottom: "100%", left: 0, right: 0, marginBottom: "0.5rem", zIndex: 1000, maxHeight: "400px", overflowY: "auto" }}>
                    {/* Games section - shown first */}
                    {gameSearchResults.length > 0 && (
                      <>
                        <div style={{ padding: "0.5rem", fontWeight: "bold", fontSize: "0.9rem", backgroundColor: "rgba(0,0,0,0.05)", borderBottom: "1px solid #ddd" }}>
                          Games
                        </div>
                        {gameSearchResults.map((game) => {
                          const textBeforeCursor = input.substring(0, cursorPosition);
                          const lastAtIndex = textBeforeCursor.lastIndexOf('@');
                          const query = lastAtIndex !== -1 ? textBeforeCursor.substring(lastAtIndex + 1).trim() : '';

                          const highlightMatch = (text, query) => {
                            if (!query) return text;
                            const words = query.split(/\s+/).filter(w => w.length > 0);
                            if (words.length === 0) return text;
                            const pattern = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
                            const regex = new RegExp(`(${pattern})`, 'gi');
                            const parts = text.split(regex);
                            return parts.map((part, idx) =>
                              regex.test(part) ? <mark key={idx} style={{ backgroundColor: '#ffeb3b', padding: '0 2px' }}>{part}</mark> : part
                            );
                          };

                          return (
                            <div
                              key={game.id}
                              className="game-search-item"
                              onClick={() => handleGameSelectFromMention(game)}
                            >
                              <div style={{ fontWeight: "bold" }}>
                                {highlightMatch(game.name, query)}
                                {game.year_published && ` (${game.year_published})`}
                              </div>
                              {game.features && game.features.length > 0 && (
                                <div style={{ fontSize: "0.85rem", opacity: 0.7, marginTop: "0.25rem" }}>
                                  {game.features.slice(0, 5).map((f, idx) => (
                                    <span key={idx} style={{ marginRight: "0.5rem" }}>
                                      {f[0]} {f[1]}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </>
                    )}

                    {/* Features section - shown after games, ordered: mechanics, categories, designers, artists */}
                    {featureSearchResults.length > 0 && (
                      <>
                        {gameSearchResults.length > 0 && (
                          <div style={{ padding: "0.5rem", fontWeight: "bold", fontSize: "0.9rem", backgroundColor: "rgba(0,0,0,0.05)", borderTop: "1px solid #ddd", borderBottom: "1px solid #ddd" }}>
                            Features
                          </div>
                        )}
                        {!gameSearchResults.length && (
                          <div style={{ padding: "0.5rem", fontWeight: "bold", fontSize: "0.9rem", backgroundColor: "rgba(0,0,0,0.05)", borderBottom: "1px solid #ddd" }}>
                            Features
                          </div>
                        )}
                        {featureSearchResults.map((feature) => {
                          const textBeforeCursor = input.substring(0, cursorPosition);
                          const lastAtIndex = textBeforeCursor.lastIndexOf('@');
                          const query = lastAtIndex !== -1 ? textBeforeCursor.substring(lastAtIndex + 1).trim() : '';

                          const highlightMatch = (text, query) => {
                            if (!query) return text;
                            const words = query.split(/\s+/).filter(w => w.length > 0);
                            if (words.length === 0) return text;
                            const pattern = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
                            const regex = new RegExp(`(${pattern})`, 'gi');
                            const parts = text.split(regex);
                            return parts.map((part, idx) =>
                              regex.test(part) ? <mark key={idx} style={{ backgroundColor: '#ffeb3b', padding: '0 2px' }}>{part}</mark> : part
                            );
                          };

                          return (
                            <div
                              key={`${feature.type}-${feature.id}`}
                              className="game-search-item feature-search-item"
                              onClick={() => selectFeature(feature)}
                              style={{ paddingLeft: "2rem" }}
                            >
                              <div>
                                <span style={{ marginRight: "0.5rem" }}>{feature.icon}</span>
                                <span style={{ fontWeight: "500" }}>{highlightMatch(feature.name, query)}</span>
                                <span style={{ fontSize: "0.85rem", opacity: 0.7, marginLeft: "0.5rem" }}>
                                  ({feature.type})
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Filter ribbon below input */}
              <div className="filter-ribbon">
                  <div className="filter-ribbon-content">
                    {/* Filter controls */}
                    <div className="filter-controls-compact">
                      <div className="filter-selector-group">
                        <label htmlFor="player-count-select" className="filter-label">👥 Players:</label>
                        <select
                          id="player-count-select"
                          value={playerCount || ''}
                          onChange={(e) => handlePlayerCountChange(e.target.value)}
                          className="filter-select"
                          aria-label="Select number of players"
                        >
                          <option value="">Any</option>
                          {PLAYER_COUNTS.map((count) => (
                            <option key={count} value={count}>
                              {count} {count === 1 ? 'player' : 'players'}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="filter-selector-group">
                        <label htmlFor="playtime-select" className="filter-label">⏱️ Playtime:</label>
                        <select
                          id="playtime-select"
                          value={playtime || ''}
                          onChange={(e) => handlePlaytimeChange(e.target.value)}
                          className="filter-select"
                          aria-label="Select playtime"
                        >
                          <option value="">Any</option>
                          {PLAYTIME_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="chip toggle">
                        <label>
                          <input
                            type="checkbox"
                            checked={useCollection}
                            onChange={(e) => setUseCollection(e.target.checked)}
                            aria-label="Filter to games in my collection"
                          />
                          In my collection
                        </label>
                      </div>
                      {gameChips.length > 0 && excludedFamilies.length > 0 && (
                        <div className="chip toggle">
                          <label>
                            <input
                              type="checkbox"
                              checked={excludeSameSeries}
                              onChange={(e) => setExcludeSameSeries(e.target.checked)}
                              aria-label="Exclude same series/families"
                            />
                            Exclude same series
                          </label>
                        </div>
                      )}
                      <div className="chip toggle">
                        <label>
                          <input
                            type="checkbox"
                            checked={excludeImplementationCategories}
                            onChange={(e) => setExcludeImplementationCategories(e.target.checked)}
                            aria-label="Exclude implementation categories"
                          />
                          Exclude implementation categories
                        </label>
                      </div>
                      <button
                        className="filters-overlay-button"
                        onClick={() => setShowFiltersOverlay(true)}
                        aria-label="Open filters and options"
                        title="Filters & Options"
                      >
                        ⚙️ Filters
                        {(promptChips.length > 0 || gameChips.length > 0 || doINeedChips.length > 0 || chips.length > 0) && (
                          <span className="filter-badge">{promptChips.length + gameChips.length + doINeedChips.length + chips.length}</span>
                        )}
                      </button>
                    </div>

                    {/* Active filters */}
                    {(promptChips.length > 0 || gameChips.length > 0 || doINeedChips.length > 0 || chips.length > 0) && (
                      <div className="active-filters">
                        {chips.map((chip) => (
                          <span key={chip.facet} className="filter-chip">{chip.facet}</span>
                        ))}
                        {promptChips.map((prompt) => (
                          <span key={prompt} className="filter-chip">
                            {prompt}
                            <button
                              onClick={() => removePromptChip(prompt)}
                              className="filter-chip-remove"
                              aria-label={`Remove ${prompt} filter`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                        {gameChips.map((game) => (
                          <span key={game.id} className="filter-chip game-chip">
                            🎮 {game.name}
                            <button
                              onClick={() => {
                                removeGameChip(game.id);
                                // Clear exclude same series when game is removed
                                if (gameChips.length === 1) {
                                  setExcludeSameSeries(false);
                                  setExcludedFamilies([]);
                                }
                              }}
                              className="filter-chip-remove"
                              aria-label={`Remove ${game.name} filter`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                        {excludeSameSeries && excludedFamilies.length > 0 && (
                          <span className="filter-chip exclude-chip">
                            🚫 Exclude: {excludedFamilies.slice(0, 2).join(", ")}{excludedFamilies.length > 2 ? ` +${excludedFamilies.length - 2}` : ""}
                            <button
                              onClick={() => {
                                setExcludeSameSeries(false);
                                setExcludedFamilies([]);
                              }}
                              className="filter-chip-remove"
                              aria-label="Remove exclude same series filter"
                            >
                              ×
                            </button>
                          </span>
                        )}
                        {excludeImplementationCategories && (
                          <span className="filter-chip exclude-chip">
                            🚫 Exclude implementation categories
                            <button
                              onClick={() => setExcludeImplementationCategories(false)}
                              className="filter-chip-remove"
                              aria-label="Remove exclude implementation categories filter"
                            >
                              ×
                            </button>
                          </span>
                        )}
                        {doINeedChips.map((chip) => (
                          <span key={chip.id} className="filter-chip">
                            ❓ Do I need {chip.name}?
                            <button
                              onClick={() => removeDoINeedChip(chip.id)}
                              className="filter-chip-remove"
                              aria-label={`Remove ${chip.name} filter`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
          </div>
        </div>

      {/* Feedback Question Modal */}
    </div>
  );
}

// Component for ChatGPT-style slow rendering
function TypingText({ text, querySpec, highlightText, speed = 20 }) {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const textRef = useRef(text);

  useEffect(() => {
    // Reset when text changes
    if (textRef.current !== text) {
      textRef.current = text;
      setDisplayedText("");
      setIsComplete(false);
    }

    if (isComplete || !text) return;

    const fullText = text;
    let currentIndex = displayedText.length;

    const typeNextChar = () => {
      if (currentIndex < fullText.length) {
        setDisplayedText(fullText.substring(0, currentIndex + 1));
        currentIndex++;
        // Vary speed slightly for more natural feel
        const delay = speed + Math.random() * 10;
        setTimeout(typeNextChar, delay);
      } else {
        setIsComplete(true);
      }
    };

    // Start typing after a short delay
    const timeoutId = setTimeout(typeNextChar, 50);
    return () => clearTimeout(timeoutId);
  }, [text, displayedText, isComplete, speed]);

  // If text changed, reset
  useEffect(() => {
    if (textRef.current !== text) {
      textRef.current = text;
      setDisplayedText("");
      setIsComplete(false);
    }
  }, [text]);

  // Render highlighted text if querySpec exists and text is complete, otherwise plain text
  if (querySpec && isComplete) {
    return highlightText(displayedText, querySpec);
  }

  return <>{displayedText}</>;
}

function MessageList({ messages, setMessages, onGameClick, user, onLikeDislike, onFeedbackResponse, helpfulQuestion, onRequireFeature, showDislikeInput, dislikeDetails, setDislikeDetails, setShowDislikeInput, handleDislikeSubmit, onAddToSearch, showWelcomeMessage, handleWelcomeOption, onFollowupSelect }) {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

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
      {messages.length === 0 && showWelcomeMessage ? (
        <div className="welcome-message">
          <div className="welcome-content">
            <h3>Welcome to Pista! 👋</h3>
            <p>How would you like to get started?</p>
            <div className="welcome-options">
              <button
                className="welcome-option-btn"
                onClick={() => handleWelcomeOption('game_in_mind')}
              >
                <span className="welcome-option-icon">🎮</span>
                <div>
                  <strong>Do you have a game in mind?</strong>
                  <p>Search for a specific game to learn more about it</p>
                </div>
              </button>
              <button
                className="welcome-option-btn"
                onClick={() => handleWelcomeOption('exploring')}
              >
                <span className="welcome-option-icon">🔍</span>
                <div>
                  <strong>I feel like exploring</strong>
                  <p>Discover new games based on your preferences</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      ) : messages.length === 0 ? (
        <div className="empty-chat">Start a conversation to see messages here</div>
      ) : (
        messages.map((m, idx) => (
          <div key={idx} className={`msg msg--${m.role}`}>
            <div className="msg-text">
              {m.role === "assistant" ? (
                <TypingText
                  text={m.text || ""}
                  querySpec={m.querySpec}
                  highlightText={highlightText}
                  speed={15}
                />
              ) : (
                typeof m.text === 'string' ? m.text : String(m.text || '')
              )}
            </div>
            {/* Status bar for user messages */}
            {m.role === "user" && m.status && (
              <div className="message-status" style={{
                fontSize: "0.75rem",
                color: m.status === "sending" ? "#1976d2" : m.status === "sent" ? "#4caf50" : "#f44336",
                marginTop: "0.25rem",
                fontStyle: "italic"
              }}>
                {m.status === "sending" ? "Sending..." : m.status === "sent" ? "Sent" : "Error"}
              </div>
            )}
            {m.image && (
              <img src={m.image} alt="Generated" className="generated-image" />
            )}
            {m.gameDetails ? (
              <>
                <GameDetailView
                  gameDetails={m.gameDetails}
                  onGameClick={onGameClick}
                  onRequireFeature={onRequireFeature}
                  onAddToSearch={onAddToSearch}
                />
                {m.followupPrompt && (
                  <FollowupPrompt
                    prompt={m.followupPrompt}
                    messageIndex={idx}
                    onSelect={(preference) => {
                      // Send a new message with the preference
                      const preferenceText = preference === "theme" ? "1" : "2";
                      if (onFollowupSelect) {
                        onFollowupSelect(preferenceText);
                      }
                    }}
                  />
                )}
              </>
            ) : m.abTest ? (
              <ABTestResults
                abTest={m.abTest}
                onGameClick={onGameClick}
                onRequireFeature={onRequireFeature}
                messageIndex={idx}
                onFeedbackResponse={onFeedbackResponse}
                onAddToSearch={onAddToSearch}
              />
            ) : m.results && m.results.length > 0 && (
              <>
                <GameResultList
                  results={m.results}
                  onGameClick={onGameClick}
                  onRequireFeature={onRequireFeature}
                  messageIndex={idx}
                  querySpec={m.querySpec}
                  onAddToSearch={onAddToSearch}
                />
                {m.followupPrompt && (
                  <FollowupPrompt
                    prompt={m.followupPrompt}
                    messageIndex={idx}
                    onSelect={(preference) => {
                      // Send a new message with the preference
                      const preferenceText = preference === "theme" ? "1" : "2";
                      if (onFollowupSelect) {
                        onFollowupSelect(preferenceText);
                      }
                    }}
                  />
                )}
              </>
            )}
            {m.role === "assistant" && user && helpfulQuestion && !m.isFakeDoor && (
              <div className="message-feedback">
                <div className="like-dislike-buttons">
                  <button
                    className={`like-btn ${m.liked ? "active" : ""}`}
                    onClick={() => onLikeDislike(idx, "like")}
                    title="Like this response"
                  >
                    👍
                  </button>
                  <button
                    className={`dislike-btn ${m.disliked ? "active" : ""}`}
                    onClick={() => onLikeDislike(idx, "dislike")}
                    title="Dislike this response"
                  >
                    👎
                  </button>
                </div>
                {showDislikeInput[idx] && (
                  <div className="dislike-details-input" style={{ marginTop: "0.5rem", padding: "0.5rem", border: "1px solid #ddd", borderRadius: "4px" }}>
                    <textarea
                      value={dislikeDetails[idx] || ""}
                      onChange={(e) => setDislikeDetails(prev => ({ ...prev, [idx]: e.target.value }))}
                      placeholder="Optional: Tell us what could be improved..."
                      rows={3}
                      style={{ width: "100%", padding: "0.5rem", fontSize: "0.9rem", border: "1px solid #ccc", borderRadius: "4px", resize: "vertical" }}
                    />
                    <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem" }}>
                      <button
                        onClick={() => handleDislikeSubmit(idx)}
                        style={{ padding: "0.5rem 1rem", backgroundColor: "#1976d2", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
                      >
                        Submit
                      </button>
                      <button
                        onClick={() => {
                          setShowDislikeInput(prev => {
                            const newState = { ...prev };
                            delete newState[idx];
                            return newState;
                          });
                          setDislikeDetails(prev => {
                            const newState = { ...prev };
                            delete newState[idx];
                            return newState;
                          });
                          setMessages((prev) => {
                            const updated = [...prev];
                            updated[idx] = {
                              ...updated[idx],
                              disliked: false,
                            };
                            return updated;
                          });
                        }}
                        style={{ padding: "0.5rem 1rem", backgroundColor: "#ccc", color: "black", border: "none", borderRadius: "4px", cursor: "pointer" }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
                {m.feedbackQuestion && (
                  <FeedbackQuestionInline
                    question={m.feedbackQuestion}
                    messageIndex={idx}
                    onSubmit={(response) => onFeedbackResponse(idx, m.feedbackQuestion.id, response)}
                  />
                )}
              </div>
            )}
          </div>
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}

function GameDetailView({ gameDetails, onGameClick, onRequireFeature, onAddToSearch }) {
  const [showFullDescription, setShowFullDescription] = useState(false);
  const [showMoreFeatures, setShowMoreFeatures] = useState(false);

  const descriptionPreview = gameDetails.description
    ? (gameDetails.description.length > 150
        ? gameDetails.description.substring(0, 150) + "..."
        : gameDetails.description)
    : "No description available.";

  const shouldTruncateDescription = gameDetails.description && gameDetails.description.length > 150;

  return (
    <div className="game-detail-view">
      <div className="game-detail-card">
        {gameDetails.thumbnail && (
          <img
            src={gameDetails.thumbnail}
            alt={gameDetails.name}
            className="game-detail-thumbnail"
            onClick={() => onGameClick && onGameClick(gameDetails.id)}
          />
        )}
        <div className="game-detail-content">
          <h3
            className="game-detail-title"
            onClick={() => onGameClick && onGameClick(gameDetails.id)}
            style={{ cursor: "pointer", color: "#1976d2" }}
          >
            {gameDetails.name}
          </h3>

          <div className="game-detail-meta">
            {gameDetails.year_published && (
              <span>📅 {gameDetails.year_published}</span>
            )}
            {gameDetails.min_players !== null && gameDetails.max_players !== null && (
              <span>👥 {gameDetails.min_players === gameDetails.max_players
                ? `${gameDetails.min_players} players`
                : `${gameDetails.min_players}-${gameDetails.max_players} players`}
              </span>
            )}
            {gameDetails.average_rating && (
              <span>⭐ {gameDetails.average_rating.toFixed(1)} ({gameDetails.num_ratings} ratings)</span>
            )}
          </div>

          <div className="game-detail-description">
            <p>
              {showFullDescription ? gameDetails.description : descriptionPreview}
            </p>
            {shouldTruncateDescription && (
              <button
                className="show-more-btn"
                onClick={() => setShowFullDescription(!showFullDescription)}
              >
                {showFullDescription ? "Show Less" : "Show More"}
              </button>
            )}
          </div>

          <div className="game-detail-features">
            <h4>Categories</h4>
            <div className="feature-chips">
              {gameDetails.categories && gameDetails.categories.length > 0 ? (
                gameDetails.categories.map((cat, idx) => (
                  <span
                    key={idx}
                    className="feature-chip"
                    onClick={() => onRequireFeature && onRequireFeature("categories", cat)}
                    style={{ cursor: "pointer" }}
                    title="Click to search for games with this category"
                  >
                    {cat}
                  </span>
                ))
              ) : (
                <span className="no-features">No categories available</span>
              )}
            </div>

            <h4>Mechanics</h4>
            <div className="feature-chips">
              {gameDetails.mechanics && gameDetails.mechanics.length > 0 ? (
                gameDetails.mechanics.map((mech, idx) => (
                  <span
                    key={idx}
                    className="feature-chip"
                    onClick={() => onRequireFeature && onRequireFeature("mechanics", mech)}
                    style={{ cursor: "pointer" }}
                    title="Click to search for games with this mechanic"
                  >
                    {mech}
                  </span>
                ))
              ) : (
                <span className="no-features">No mechanics available</span>
              )}
            </div>

            {gameDetails.families && gameDetails.families.length > 0 && (
              <>
                {!showMoreFeatures && (
                  <button
                    className="show-more-features-btn"
                    onClick={() => setShowMoreFeatures(true)}
                  >
                    More
                  </button>
                )}
                {showMoreFeatures && (
                  <>
                    <h4>Families</h4>
                    <div className="feature-chips">
                      {gameDetails.families.map((family, idx) => (
                        <span
                          key={idx}
                          className="feature-chip"
                          onClick={() => onRequireFeature && onRequireFeature("families", family)}
                          style={{ cursor: "pointer" }}
                          title="Click to search for games in this family"
                        >
                          {family}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Component for slow rendering of tiles and chips
function TypingTiles({ results, onGameClick, onRequireFeature, messageIndex, variant, differences, expandedGames, toggleExpand, querySpec, onAddToSearch, tileDelay = 100, chipDelay = 30, onLoadMore }) {
  const [visibleTiles, setVisibleTiles] = useState([]);
  const [visibleChips, setVisibleChips] = useState({}); // { tileId: number of visible chips }
  const [displayedCount, setDisplayedCount] = useState(5); // Show 5 tiles initially

  useEffect(() => {
    if (!results || results.length === 0) return;

    // Reset when results change
    setVisibleTiles([]);
    setVisibleChips({});
    setDisplayedCount(5); // Reset to initial count

    // Render tiles one by one up to displayedCount
    let tileIndex = 0;
    const maxTiles = Math.min(displayedCount, results.length);
    const renderNextTile = () => {
      if (tileIndex < maxTiles) {
        setVisibleTiles(prev => [...prev, tileIndex]);
        tileIndex++;
        setTimeout(renderNextTile, tileDelay);
      }
    };

    // Start rendering after a short delay
    const timeoutId = setTimeout(renderNextTile, 50);
    return () => clearTimeout(timeoutId);
  }, [results, tileDelay, displayedCount]);

  // Render chips for each visible tile progressively
  useEffect(() => {
    visibleTiles.forEach((tileIdx) => {
      const game = results[tileIdx];
      if (!game || !game.game_id) return;

      const gameId = game.game_id;
      if (visibleChips[gameId] !== undefined) return; // Already started rendering chips for this tile

      // Get all chips for this tile
      const allChips = [];
      // Add shared features, missing features, extra features, etc.
      if (game.shared_mechanics) {
        game.shared_mechanics.forEach(m => allChips.push({ type: "mechanics", value: m }));
      }
      if (game.shared_categories) {
        game.shared_categories.forEach(c => allChips.push({ type: "categories", value: c }));
      }
      if (game.shared_designers) {
        game.shared_designers.forEach(d => allChips.push({ type: "designers", value: d }));
      }
      if (game.shared_families) {
        game.shared_families.forEach(f => allChips.push({ type: "families", value: f }));
      }
      if (game.missing_mechanics) {
        game.missing_mechanics.forEach(m => allChips.push({ type: "mechanics", value: m, isMissing: true }));
      }
      if (game.missing_categories) {
        game.missing_categories.forEach(c => allChips.push({ type: "categories", value: c, isMissing: true }));
      }
      if (game.extra_mechanics) {
        game.extra_mechanics.forEach(m => allChips.push({ type: "mechanics", value: m, isExtra: true }));
      }
      if (game.extra_categories) {
        game.extra_categories.forEach(c => allChips.push({ type: "categories", value: c, isExtra: true }));
      }

      if (allChips.length === 0) {
        setVisibleChips(prev => ({ ...prev, [gameId]: 0 }));
        return;
      }

      // Start rendering chips for this tile
      setVisibleChips(prev => ({ ...prev, [gameId]: 0 }));

      let chipIndex = 0;
      const renderNextChip = () => {
        if (chipIndex < allChips.length) {
          setVisibleChips(prev => ({ ...prev, [gameId]: chipIndex + 1 }));
          chipIndex++;
          setTimeout(renderNextChip, chipDelay);
        }
      };

      // Start rendering chips after tile is visible
      setTimeout(renderNextChip, tileDelay);
    });
  }, [visibleTiles, results, chipDelay, tileDelay, visibleChips]);

  if (!results || results.length === 0) {
    return null;
  }

  const handleLoadMore = () => {
    if (onLoadMore) {
      // If callback provided, use it to fetch more from backend
      onLoadMore();
    } else {
      // Otherwise, just show more from existing results
      setDisplayedCount(prev => Math.min(prev + 5, results.length));
    }
  };

  // Check if there are more results to show
  // Show button if we haven't displayed all results yet
  const hasMore = displayedCount < results.length;

  return (
    <div className="game-results">
      {visibleTiles.map((tileIdx) => {
        const r = results[tileIdx];
        if (!r || !r.game_id) return null;

        const gameId = r.game_id;
        const chipsToShow = visibleChips[gameId] || 0;

        // Render the tile (we'll pass chipsToShow to the rendering logic)
        // For now, we'll render all chips but with opacity animation
        return (
          <GameTile
            key={r.game_id}
            game={r}
            tileIdx={tileIdx}
            chipsToShow={chipsToShow}
            onGameClick={onGameClick}
            onRequireFeature={onRequireFeature}
            messageIndex={messageIndex}
            variant={variant}
            differences={differences}
            expandedGames={expandedGames}
            toggleExpand={toggleExpand}
            querySpec={querySpec}
            onAddToSearch={onAddToSearch}
          />
        );
      })}
      {hasMore && (
        <div className="load-more-tile">
          <button onClick={handleLoadMore} title="Load more results">
            +
          </button>
        </div>
      )}
    </div>
  );
}

function GameResultList({ results, onGameClick, onRequireFeature, messageIndex, variant, differences, expandedGames, toggleExpand, querySpec, onAddToSearch }) {
  // If expandedGames is passed as prop (for A/B tests), use it; otherwise create local state
  const [localExpanded, setLocalExpanded] = useState(new Set());
  const isExpanded = (gameId) => {
    if (expandedGames !== undefined) {
      return expandedGames.has(gameId);
    }
    return localExpanded.has(gameId);
  };
  const handleToggleExpand = (gameId) => {
    if (toggleExpand) {
      toggleExpand(gameId);
    } else {
      setLocalExpanded((prev) => {
        const newSet = new Set(prev);
        if (newSet.has(gameId)) {
          newSet.delete(gameId);
        } else {
          newSet.add(gameId);
        }
        return newSet;
      });
    }
  };

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <TypingTiles
      results={results}
      onGameClick={onGameClick}
      onRequireFeature={onRequireFeature}
      messageIndex={messageIndex}
      variant={variant}
      differences={differences}
      expandedGames={expandedGames}
      toggleExpand={handleToggleExpand}
      querySpec={querySpec}
      onAddToSearch={onAddToSearch}
    />
  );
}

// Helper component to render a single game tile with slow chip rendering
function GameTile({ game: r, tileIdx, chipsToShow, onGameClick, onRequireFeature, messageIndex, variant, differences, expandedGames, toggleExpand, querySpec, onAddToSearch }) {
  // Check if game is expanded using expandedGames prop
  const isExpanded = (gameId) => {
    if (expandedGames !== undefined) {
      return expandedGames.has(gameId);
    }
    return false;
  };

  const handleToggleExpand = (gameId) => {
    if (toggleExpand) {
      toggleExpand(gameId);
    }
  };

  // Check if this is a collection_recommendation result
  const isCollectionRecommendation = querySpec?.intent === "collection_recommendation" &&
    (r.missing_mechanics || r.missing_categories || r.extra_mechanics || r.extra_categories);

  // Extract features
  const sharedFeatures = [];
  const hasAllFeatures = r.mechanics || r.categories || r.designers_list || r.families;

  if (hasAllFeatures) {
    if (r.mechanics) {
      r.mechanics.forEach(m => sharedFeatures.push({ type: "mechanics", value: m }));
    }
    if (r.categories) {
      r.categories.forEach(c => sharedFeatures.push({ type: "categories", value: c }));
    }
    if (r.designers_list) {
      r.designers_list.forEach(d => sharedFeatures.push({ type: "designers", value: d }));
    }
    if (r.families) {
      r.families.forEach(f => sharedFeatures.push({ type: "families", value: f }));
    }
  } else {
    if (r.shared_mechanics) {
      r.shared_mechanics.forEach(m => sharedFeatures.push({ type: "mechanics", value: m }));
    }
    if (r.shared_categories) {
      r.shared_categories.forEach(c => sharedFeatures.push({ type: "categories", value: c }));
    }
    if (r.shared_designers) {
      r.shared_designers.forEach(d => sharedFeatures.push({ type: "designers", value: d }));
    }
    if (r.shared_families) {
      r.shared_families.forEach(f => sharedFeatures.push({ type: "families", value: f }));
    }
  }

  const missingFeatures = [];
  const extraFeatures = [];
  if (isCollectionRecommendation) {
    if (r.missing_mechanics) {
      r.missing_mechanics.forEach(m => missingFeatures.push({ type: "mechanics", value: m }));
    }
    if (r.missing_categories) {
      r.missing_categories.forEach(c => missingFeatures.push({ type: "categories", value: c }));
    }
    if (r.missing_designers) {
      r.missing_designers.forEach(d => missingFeatures.push({ type: "designers", value: d }));
    }
    if (r.missing_families) {
      r.missing_families.forEach(f => missingFeatures.push({ type: "families", value: f }));
    }
    if (r.extra_mechanics) {
      r.extra_mechanics.forEach(m => extraFeatures.push({ type: "mechanics", value: m }));
    }
    if (r.extra_categories) {
      r.extra_categories.forEach(c => extraFeatures.push({ type: "categories", value: c }));
    }
    if (r.extra_designers) {
      r.extra_designers.forEach(d => extraFeatures.push({ type: "designers", value: d }));
    }
    if (r.extra_families) {
      r.extra_families.forEach(f => extraFeatures.push({ type: "families", value: f }));
    }
  }

  const isUnique = variant && differences && (
    (variant === "A" && differences.onlyInA.some(g => g.game_id === r.game_id)) ||
    (variant === "B" && differences.onlyInB.some(g => g.game_id === r.game_id))
  );

  // Get all chips for this tile
  const allChips = [...sharedFeatures, ...missingFeatures, ...extraFeatures];
  const visibleChips = allChips.slice(0, chipsToShow);

  return (
    <div
      className={`game-card ${isUnique ? "ab-test-unique" : ""}`}
      key={r.game_id}
      style={{
        border: isUnique ? "2px solid #1976d2" : undefined,
        backgroundColor: isUnique ? "rgba(25, 118, 210, 0.05)" : undefined,
        display: "flex",
        gap: "1rem",
        alignItems: "flex-start",
        opacity: chipsToShow === 0 ? 0.3 : 1,
        transition: "opacity 0.3s ease-in"
      }}
    >
      <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start", flex: 1 }}>
        {r.thumbnail && (
          <img
            src={r.thumbnail}
            alt={r.name || "Game"}
            style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "4px" }}
          />
        )}
        <div style={{ flex: 1 }}>
          <div
            className="game-card__title"
            style={{ cursor: "pointer", color: "#1976d2" }}
            onClick={(e) => {
              e.stopPropagation();
              if (onAddToSearch) {
                onAddToSearch(r.name || `Game ${r.game_id}`, 'game', r.game_id);
              }
            }}
            title="Click to search for this game"
          >
            {r.name || `Game ${r.game_id}`}
          </div>
          <div className="game-card__meta">
            {r.designers && r.designers.length > 0 && (
              <span style={{ marginRight: "1rem", fontSize: "0.9em", opacity: 0.8 }}>
                👤 {r.designers.map((designer, idx) => (
                  <span key={idx}>
                    <span
                      style={{ cursor: "pointer", color: "#1976d2", textDecoration: "underline" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onAddToSearch) {
                          onAddToSearch(designer, 'designer');
                        }
                      }}
                      title="Click to search for this designer"
                    >
                      {designer}
                    </span>
                    {idx < r.designers.length - 1 && ", "}
                  </span>
                ))}
              </span>
            )}
            {r.year_published && (
              <span style={{ marginRight: "1rem", fontSize: "0.9em", opacity: 0.8 }}>
                📅 {r.year_published}
              </span>
            )}
            {(r.similarity_score !== undefined && r.similarity_score !== null) ||
             (r.final_score !== undefined && r.final_score !== null) ||
             (r.embedding_similarity !== undefined && r.embedding_similarity !== null) ? (
              <span style={{
                fontWeight: isCollectionRecommendation ? "bold" : "normal",
                color: isCollectionRecommendation ? "#1976d2" : "inherit"
              }}>
                Similarity:{" "}
                {r.similarity_score !== undefined && r.similarity_score !== null
                  ? (r.similarity_score * 100).toFixed(1) + "%"
                  : (r.final_score !== undefined && r.final_score !== null
                      ? (r.final_score * 100).toFixed(1) + "%"
                      : (r.embedding_similarity !== undefined && r.embedding_similarity !== null
                          ? (r.embedding_similarity * 100).toFixed(1) + "%"
                          : "N/A"))}
              </span>
            ) : null}
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
          {r.description && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleToggleExpand(r.game_id);
              }}
              style={{
                marginTop: "0.5rem",
                padding: "0.25rem 0.5rem",
                fontSize: "0.85rem",
                border: "1px solid #ddd",
                borderRadius: "4px",
                background: "transparent",
                cursor: "pointer"
              }}
            >
              {isExpanded(r.game_id) ? "Show less" : "Show more"}
            </button>
          )}
          {isExpanded(r.game_id) && r.description && (
            <div style={{ marginTop: "0.5rem", padding: "0.5rem", backgroundColor: "var(--bg-secondary, #f5f5f5)", borderRadius: "4px", fontSize: "0.9rem", lineHeight: "1.5" }}>
              {r.description}
            </div>
          )}
          {/* Render chips progressively */}
          {isCollectionRecommendation ? (
            <div style={{ marginTop: "0.5rem" }}>
              {sharedFeatures.length > 0 && (
                <div style={{ marginBottom: "0.5rem" }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#4caf50" }}>
                    ✓ Similarities:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                    {sharedFeatures.slice(0, chipsToShow).map((feature, idx) => (
                      <span
                        key={`shared-${feature.type}-${feature.value}-${idx}`}
                        style={{
                          padding: "0.25rem 0.5rem",
                          backgroundColor: "#e8f5e9",
                          border: "1px solid #4caf50",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                          color: "#2e7d32",
                          opacity: idx < chipsToShow ? 1 : 0,
                          transition: "opacity 0.2s ease-in"
                        }}
                      >
                        {feature.value}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {missingFeatures.length > 0 && (
                <div style={{ marginBottom: "0.5rem" }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#ff9800" }}>
                    + Missing (in target game):
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                    {missingFeatures.slice(0, Math.max(0, chipsToShow - sharedFeatures.length)).map((feature, idx) => (
                      <span
                        key={`missing-${feature.type}-${feature.value}-${idx}`}
                        style={{
                          padding: "0.25rem 0.5rem",
                          backgroundColor: "#fff3e0",
                          border: "1px solid #ff9800",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                          color: "#e65100",
                          opacity: (sharedFeatures.length + idx) < chipsToShow ? 1 : 0,
                          transition: "opacity 0.2s ease-in"
                        }}
                      >
                        {feature.value}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {extraFeatures.length > 0 && (
                <div style={{ marginBottom: "0.5rem" }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#2196f3" }}>
                    - Extra (in your collection game):
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                    {extraFeatures.slice(0, Math.max(0, chipsToShow - sharedFeatures.length - missingFeatures.length)).map((feature, idx) => (
                      <span
                        key={`extra-${feature.type}-${feature.value}-${idx}`}
                        style={{
                          padding: "0.25rem 0.5rem",
                          backgroundColor: "#e3f2fd",
                          border: "1px solid #2196f3",
                          borderRadius: "4px",
                          fontSize: "0.85rem",
                          color: "#1565c0",
                          opacity: (sharedFeatures.length + missingFeatures.length + idx) < chipsToShow ? 1 : 0,
                          transition: "opacity 0.2s ease-in"
                        }}
                      >
                        {feature.value}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ marginTop: "0.5rem" }}>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                {visibleChips.map((feature, idx) => (
                  <span
                    key={`feature-${feature.type}-${feature.value}-${idx}`}
                    style={{
                      padding: "0.25rem 0.5rem",
                      backgroundColor: "#e3f2fd",
                      border: "1px solid #2196f3",
                      borderRadius: "4px",
                      fontSize: "0.85rem",
                      color: "#1565c0",
                      opacity: idx < chipsToShow ? 1 : 0,
                      transition: "opacity 0.2s ease-in",
                      cursor: onRequireFeature ? "pointer" : "default"
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onRequireFeature) {
                        // onRequireFeature expects (messageIndex, featureType, featureValue)
                        onRequireFeature(messageIndex, feature.type, feature.value);
                      }
                    }}
                    title={onRequireFeature ? "Click to add to search" : undefined}
                  >
                    {feature.value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// eslint-disable-next-line no-unused-vars
// Keep the original GameResultList for backward compatibility, but use TypingTiles
function GameResultListOriginal({ results, onGameClick, onRequireFeature, messageIndex, variant, differences, expandedGames, toggleExpand, querySpec, onAddToSearch }) {
  // If expandedGames is passed as prop (for A/B tests), use it; otherwise create local state
  const [localExpanded, setLocalExpanded] = useState(new Set());
  const isExpanded = (gameId) => {
    if (expandedGames !== undefined) {
      return expandedGames.has(gameId);
    }
    return localExpanded.has(gameId);
  };
  const handleToggleExpand = (gameId) => {
    if (toggleExpand) {
      toggleExpand(gameId);
    } else {
      setLocalExpanded((prev) => {
        const newSet = new Set(prev);
        if (newSet.has(gameId)) {
          newSet.delete(gameId);
        } else {
          newSet.add(gameId);
        }
        return newSet;
      });
    }
  };

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <div className="game-results">
      {results
        .filter(r => r && r.game_id) // Filter out invalid results
        .map((r) => {
          // Check if this is a collection_recommendation result (has missing_* or extra_* fields)
          const isCollectionRecommendation = querySpec?.intent === "collection_recommendation" &&
            (r.missing_mechanics || r.missing_categories || r.extra_mechanics || r.extra_categories);

          // Extract features - use all features if available (feature-only search), otherwise use shared features (similarity search)
          const sharedFeatures = [];
          // Check if this is a feature-only search result (has all features, not shared)
          const hasAllFeatures = r.mechanics || r.categories || r.designers_list || r.families;

          if (hasAllFeatures) {
            // Feature-only search: use all features
            if (r.mechanics) {
              r.mechanics.forEach(m => sharedFeatures.push({ type: "mechanics", value: m }));
            }
            if (r.categories) {
              r.categories.forEach(c => sharedFeatures.push({ type: "categories", value: c }));
            }
            if (r.designers_list) {
              r.designers_list.forEach(d => sharedFeatures.push({ type: "designers", value: d }));
            }
            if (r.families) {
              r.families.forEach(f => sharedFeatures.push({ type: "families", value: f }));
            }
          } else {
            // Similarity search: use shared features
            if (r.shared_mechanics) {
              r.shared_mechanics.forEach(m => sharedFeatures.push({ type: "mechanics", value: m }));
            }
            if (r.shared_categories) {
              r.shared_categories.forEach(c => sharedFeatures.push({ type: "categories", value: c }));
            }
            if (r.shared_designers) {
              r.shared_designers.forEach(d => sharedFeatures.push({ type: "designers", value: d }));
            }
            if (r.shared_families) {
              r.shared_families.forEach(f => sharedFeatures.push({ type: "families", value: f }));
            }
          }

          // Extract missing and extra features for collection recommendation
          const missingFeatures = [];
          const extraFeatures = [];
          if (isCollectionRecommendation) {
            if (r.missing_mechanics) {
              r.missing_mechanics.forEach(m => missingFeatures.push({ type: "mechanics", value: m }));
            }
            if (r.missing_categories) {
              r.missing_categories.forEach(c => missingFeatures.push({ type: "categories", value: c }));
            }
            if (r.missing_designers) {
              r.missing_designers.forEach(d => missingFeatures.push({ type: "designers", value: d }));
            }
            if (r.missing_families) {
              r.missing_families.forEach(f => missingFeatures.push({ type: "families", value: f }));
            }
            if (r.extra_mechanics) {
              r.extra_mechanics.forEach(m => extraFeatures.push({ type: "mechanics", value: m }));
            }
            if (r.extra_categories) {
              r.extra_categories.forEach(c => extraFeatures.push({ type: "categories", value: c }));
            }
            if (r.extra_designers) {
              r.extra_designers.forEach(d => extraFeatures.push({ type: "designers", value: d }));
            }
            if (r.extra_families) {
              r.extra_families.forEach(f => extraFeatures.push({ type: "families", value: f }));
            }
          }

          // Check if this game is unique to this variant (for highlighting)
          const isUnique = variant && differences && (
            (variant === "A" && differences.onlyInA.some(g => g.game_id === r.game_id)) ||
            (variant === "B" && differences.onlyInB.some(g => g.game_id === r.game_id))
          );

          return (
            <div
              className={`game-card ${isUnique ? "ab-test-unique" : ""}`}
              key={r.game_id}
              style={{
                border: isUnique ? "2px solid #1976d2" : undefined,
                backgroundColor: isUnique ? "rgba(25, 118, 210, 0.05)" : undefined,
                display: "flex",
                gap: "1rem",
                alignItems: "flex-start"
              }}
            >
              <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start", flex: 1 }}>
                {r.thumbnail && (
                  <img
                    src={r.thumbnail}
                    alt={r.name || "Game"}
                    style={{ width: "80px", height: "80px", objectFit: "cover", borderRadius: "4px" }}
                  />
                )}
                <div style={{ flex: 1 }}>
                  <div
                    className="game-card__title"
                    style={{ cursor: "pointer", color: "#1976d2" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onAddToSearch) {
                        onAddToSearch(r.name || `Game ${r.game_id}`, 'game', r.game_id);
                      }
                    }}
                    title="Click to search for this game"
                  >
                    {r.name || `Game ${r.game_id}`}
                  </div>
                  <div className="game-card__meta">
                    {r.designers && r.designers.length > 0 && (
                      <span style={{ marginRight: "1rem", fontSize: "0.9em", opacity: 0.8 }}>
                        👤 {r.designers.map((designer, idx) => (
                          <span key={idx}>
                            <span
                              style={{ cursor: "pointer", color: "#1976d2", textDecoration: "underline" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onAddToSearch) {
                                  onAddToSearch(designer, 'designer');
                                }
                              }}
                              title="Click to search for this designer"
                            >
                              {designer}
                            </span>
                            {idx < r.designers.length - 1 && ", "}
                          </span>
                        ))}
                      </span>
                    )}
                    {r.year_published && (
                      <span style={{ marginRight: "1rem", fontSize: "0.9em", opacity: 0.8 }}>
                        📅 {r.year_published}
                      </span>
                    )}
                    {/* Show similarity score - especially important for collection recommendation */}
                    {(r.similarity_score !== undefined && r.similarity_score !== null) ||
                     (r.final_score !== undefined && r.final_score !== null) ||
                     (r.embedding_similarity !== undefined && r.embedding_similarity !== null) ? (
                      <span style={{
                        fontWeight: isCollectionRecommendation ? "bold" : "normal",
                        color: isCollectionRecommendation ? "#1976d2" : "inherit"
                      }}>
                        Similarity:{" "}
                        {r.similarity_score !== undefined && r.similarity_score !== null
                          ? (r.similarity_score * 100).toFixed(1) + "%"
                          : (r.final_score !== undefined && r.final_score !== null
                              ? (r.final_score * 100).toFixed(1) + "%"
                              : (r.embedding_similarity !== undefined && r.embedding_similarity !== null
                                  ? (r.embedding_similarity * 100).toFixed(1) + "%"
                                  : "N/A"))}
                      </span>
                    ) : null}
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
                  {r.description && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleExpand(r.game_id);
                      }}
                      style={{
                        marginTop: "0.5rem",
                        padding: "0.25rem 0.5rem",
                        fontSize: "0.85rem",
                        border: "1px solid #ddd",
                        borderRadius: "4px",
                        background: "transparent",
                        cursor: "pointer"
                      }}
                    >
                      {isExpanded(r.game_id) ? "Show less" : "Show more"}
                    </button>
                  )}
                  {isExpanded(r.game_id) && r.description && (
                    <div style={{ marginTop: "0.5rem", padding: "0.5rem", backgroundColor: "var(--bg-secondary, #f5f5f5)", borderRadius: "4px", fontSize: "0.9rem", lineHeight: "1.5" }}>
                      {r.description}
                    </div>
                  )}
                  {/* Show similarities and differences for collection recommendation, or shared features for regular search */}
                  {isCollectionRecommendation ? (
                    <div style={{ marginTop: "0.5rem" }}>
                      {/* Similarities (shared features) */}
                      {sharedFeatures.length > 0 && (
                        <div style={{ marginBottom: "0.5rem" }}>
                          <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#4caf50" }}>
                            ✓ Similarities:
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                            {sharedFeatures.map((feature, idx) => (
                              <span
                                key={`shared-${feature.type}-${feature.value}-${idx}`}
                                style={{
                                  padding: "0.25rem 0.5rem",
                                  backgroundColor: "#e8f5e9",
                                  border: "1px solid #4caf50",
                                  borderRadius: "4px",
                                  fontSize: "0.85rem",
                                  color: "#2e7d32"
                                }}
                              >
                                {feature.value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {/* Differences - Missing (in target game but not in collection game) */}
                      {missingFeatures.length > 0 && (
                        <div style={{ marginBottom: "0.5rem" }}>
                          <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#ff9800" }}>
                            + Missing (in target game):
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                            {missingFeatures.map((feature, idx) => (
                              <span
                                key={`missing-${feature.type}-${feature.value}-${idx}`}
                                style={{
                                  padding: "0.25rem 0.5rem",
                                  backgroundColor: "#fff3e0",
                                  border: "1px solid #ff9800",
                                  borderRadius: "4px",
                                  fontSize: "0.85rem",
                                  color: "#e65100"
                                }}
                              >
                                {feature.value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {/* Differences - Extra (in collection game but not in target game) */}
                      {extraFeatures.length > 0 && (
                        <div style={{ marginBottom: "0.5rem" }}>
                          <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#2196f3" }}>
                            - Extra (in your collection game):
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                            {extraFeatures.map((feature, idx) => (
                              <span
                                key={`extra-${feature.type}-${feature.value}-${idx}`}
                                style={{
                                  padding: "0.25rem 0.5rem",
                                  backgroundColor: "#e3f2fd",
                                  border: "1px solid #2196f3",
                                  borderRadius: "4px",
                                  fontSize: "0.85rem",
                                  color: "#1565c0"
                                }}
                              >
                                {feature.value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {sharedFeatures.length === 0 && missingFeatures.length === 0 && extraFeatures.length === 0 && (
                        <span style={{ fontSize: "0.8rem", opacity: 0.6, fontStyle: "italic" }}>
                          No feature comparison available
                        </span>
                      )}
                    </div>
                  ) : (
                    <div style={{ marginTop: "0.5rem" }}>
                      {/* Show shared features with highlighting similar to "Do I need" */}
                      {sharedFeatures.length > 0 && (
                        <div style={{ marginBottom: "0.5rem" }}>
                          <div style={{ fontSize: "0.85rem", fontWeight: "bold", marginBottom: "0.25rem", color: "#4caf50" }}>
                            ✓ Similarities:
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                            {sharedFeatures.map((feature, idx) => (
                              <span
                                key={`shared-${feature.type}-${feature.value}-${idx}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (onRequireFeature) {
                                    onRequireFeature(messageIndex, feature.type, feature.value);
                                  }
                                }}
                                title={`Click to require ${feature.value} (exclude games without this feature)`}
                                style={{
                                  padding: "0.25rem 0.5rem",
                                  backgroundColor: "#e8f5e9",
                                  border: "1px solid #4caf50",
                                  borderRadius: "4px",
                                  fontSize: "0.85rem",
                                  color: "#2e7d32",
                                  cursor: "pointer"
                                }}
                              >
                                {feature.value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {sharedFeatures.length === 0 && (
                        <span style={{ fontSize: "0.8rem", opacity: 0.6, fontStyle: "italic" }}>
                          No shared features available
                        </span>
                      )}
                    </div>
                  )}
                  {r.language_dependence && r.language_dependence.level >= 4 && r.language_dependence.level !== 81 && r.language_dependence.level !== 51 && (
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
                {/* Marketplace button on the right side */}
                {onGameClick && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onGameClick(r);
                    }}
                    style={{
                      padding: "0.5rem",
                      border: "1px solid #ddd",
                      borderRadius: "4px",
                      backgroundColor: "var(--bg-secondary, #f5f5f5)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minWidth: "40px",
                      height: "40px",
                      alignSelf: "flex-start"
                    }}
                    title="View marketplace"
                  >
                    🛒
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

function ABTestResults({ abTest, onGameClick, onRequireFeature, messageIndex, onFeedbackResponse, onAddToSearch }) {
  const [expandedGames, setExpandedGames] = useState({ a: new Set(), b: new Set() });

  const toggleExpand = (variant, gameId) => {
    setExpandedGames((prev) => {
      const newExpanded = { ...prev };
      const key = variant === "A" ? "a" : "b";
      const newSet = new Set(newExpanded[key]);
      if (newSet.has(gameId)) {
        newSet.delete(gameId);
      } else {
        newSet.add(gameId);
      }
      newExpanded[key] = newSet;
      return newExpanded;
    });
  };

  // Find differences between A and B results
  const getDifferences = () => {
    const resultsA = abTest.response_a.results || [];
    const resultsB = abTest.response_b.results || [];
    const gameIdsA = new Set(resultsA.map(r => r.game_id));
    const gameIdsB = new Set(resultsB.map(r => r.game_id));

    const onlyInA = resultsA.filter(r => !gameIdsB.has(r.game_id));
    const onlyInB = resultsB.filter(r => !gameIdsA.has(r.game_id));
    const inBoth = resultsA.filter(r => gameIdsB.has(r.game_id));

    return { onlyInA, onlyInB, inBoth };
  };

  const differences = getDifferences();

  return (
    <div className="ab-test-results">
      <div className="ab-test-header">
        <h4>{abTest.config_name}</h4>
      </div>
      <div className="ab-test-columns">
        <div className="ab-test-column">
          <div className="ab-test-label">{abTest.response_a.label}</div>
          <GameResultList
            results={abTest.response_a.results}
            onGameClick={onGameClick}
            onRequireFeature={onRequireFeature}
            messageIndex={messageIndex}
            variant="A"
            differences={differences}
            expandedGames={expandedGames.a}
            toggleExpand={(gameId) => toggleExpand("A", gameId)}
            onAddToSearch={onAddToSearch}
          />
        </div>
        <div className="ab-test-column">
          <div className="ab-test-label">{abTest.response_b.label}</div>
          <GameResultList
            results={abTest.response_b.results}
            onGameClick={onGameClick}
            onRequireFeature={onRequireFeature}
            messageIndex={messageIndex}
            variant="B"
            differences={differences}
            expandedGames={expandedGames.b}
            toggleExpand={(gameId) => toggleExpand("B", gameId)}
            onAddToSearch={onAddToSearch}
          />
        </div>
      </div>
      {abTest.question_id && (
        <div className="ab-test-question" style={{ marginTop: "1rem", padding: "1rem", borderTop: "1px solid #ddd" }}>
          <FeedbackQuestionInline
            question={{
              id: abTest.question_id,
              question_text: abTest.question_text,
              question_type: abTest.question_type,
              options: abTest.options
            }}
            messageIndex={messageIndex}
            onSubmit={(response) => onFeedbackResponse(messageIndex, abTest.question_id, response)}
          />
        </div>
      )}
    </div>
  );
}

function FollowupPrompt({ prompt, messageIndex, onSelect }) {
  // Parse the prompt to extract options
  // Expected format: "Do you prefer 1) the theme, or 2) the mechanics?"
  const themeMatch = prompt.match(/1\)\s*(the\s+)?theme/i);
  const mechanicsMatch = prompt.match(/2\)\s*(the\s+)?mechanics/i);

  return (
    <div className="followup-prompt">
      <div className="followup-prompt-text">
        {prompt}
      </div>
      <div className="followup-prompt-options">
        {themeMatch && (
          <button
            className="followup-prompt-option"
            onClick={() => onSelect("theme")}
          >
            1) The theme
          </button>
        )}
        {mechanicsMatch && (
          <button
            className="followup-prompt-option"
            onClick={() => onSelect("mechanics")}
          >
            2) The mechanics
          </button>
        )}
      </div>
    </div>
  );
}

function FeedbackQuestionInline({ question, messageIndex, onSubmit }) {
  const [response, setResponse] = useState("");
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedOptions, setSelectedOptions] = useState([]); // For multi-select

  const handleSubmit = () => {
    if (question.question_type === "text") {
      if (response.trim()) {
        onSubmit(response);
        setResponse("");
      }
    } else if (question.question_type === "single_select") {
      if (selectedOption) {
        onSubmit(selectedOption);
        setSelectedOption(null);
      }
    } else if (question.question_type === "multi_select") {
      if (selectedOptions.length > 0) {
        onSubmit(selectedOptions);
        setSelectedOptions([]);
      }
    }
  };

  const handleMultiSelectToggle = (option) => {
    setSelectedOptions(prev => {
      const exists = prev.find(o => o.id === option.id);
      if (exists) {
        return prev.filter(o => o.id !== option.id);
      } else {
        return [...prev, option];
      }
    });
  };

  // Ensure options is an array
  const options = question.options || [];

  return (
    <div className="feedback-question-inline">
      <div className="feedback-question-text">{question.question_text}</div>

      {question.question_type === "single_select" && options.length > 0 ? (
        <div className="feedback-options-inline">
          {options.map((option, idx) => {
            const optionId = option.id;
            const optionText = option.text || option;
            return (
              <button
                key={optionId || idx}
                type="button"
                className={`feedback-option-inline ${selectedOption?.id === optionId ? "selected" : ""}`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setSelectedOption(option);
                  onSubmit(option);
                }}
              >
                {optionText}
              </button>
            );
          })}
        </div>
      ) : question.question_type === "multi_select" && options.length > 0 ? (
        <div className="feedback-multiselect-inline">
          {options.map((option, idx) => {
            const optionId = option.id;
            const optionText = option.text || option;
            const isSelected = selectedOptions.some(o => o.id === optionId);
            return (
              <button
                key={optionId || idx}
                type="button"
                className={`feedback-option-inline ${isSelected ? "selected" : ""}`}
                onClick={() => handleMultiSelectToggle(option)}
              >
                {optionText}
              </button>
            );
          })}
          <button
            type="button"
            className="feedback-submit-inline"
            onClick={handleSubmit}
            disabled={selectedOptions.length === 0}
          >
            Submit
          </button>
        </div>
      ) : question.question_type === "text" ? (
        <div className="feedback-text-inline">
          <textarea
            className="feedback-textarea-inline"
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            placeholder="Your feedback..."
            rows={3}
          />
          <button
            type="button"
            className="feedback-submit-inline"
            onClick={handleSubmit}
            disabled={!response.trim()}
          >
            Submit
          </button>
        </div>
      ) : (
        <div className="feedback-error">Invalid question type or missing options</div>
      )}
    </div>
  );
}

export default PistaChat;
