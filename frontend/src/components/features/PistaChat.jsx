// frontend/src/components/features/PistaChat.jsx
import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";
import Marketplace from "./Marketplace";
import GameFeaturesEditor from "./GameFeaturesEditor";
import ScoringPad from "./ScoringPad";
import { getAnonymousUserId, hasExceededLimit, incrementMessageCount, getRemainingMessages } from "../../utils/anonymousUser";

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
  const [useCollection, setUseCollection] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [gameSearchResults, setGameSearchResults] = useState([]);
  const [featureSearchResults, setFeatureSearchResults] = useState([]);
  const [showGameSearch, setShowGameSearch] = useState(false);
  const [atMentionActive, setAtMentionActive] = useState(false);
  const [atMentionPosition, setAtMentionPosition] = useState(0);
  const [atMentionQuery, setAtMentionQuery] = useState("");
  const [searchDebounceTimer, setSearchDebounceTimer] = useState(null);
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
  
  // Note: requiredFeatures state is managed via setRequiredFeatures in handleRequireFeature and removeRequiredFeature

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
      loadHelpfulQuestion();
    }
  }, [loadChatHistory, user]);

  const loadHelpfulQuestion = async () => {
    try {
      const res = await fetch(`${API_BASE}/feedback/questions/helpful`, {
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

  const handleGameSearch = async (query) => {
    // Allow spaces and multiple keywords - trim but don't restrict
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) {
      setGameSearchResults([]);
      setFeatureSearchResults([]);
      setShowGameSearch(false);
      return;
    }
    
    // Clear existing debounce timer
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
    
    // Debounce search to avoid too many requests
    const timer = setTimeout(async () => {
      try {
        // Increase limit to 20 for better results
        const res = await fetch(`${API_BASE}/games/search?q=${encodeURIComponent(trimmedQuery)}&limit=20`);
        if (res.ok) {
          const data = await res.json();
          // Handle both old format (array) and new format (object with games/features)
          if (Array.isArray(data)) {
            setGameSearchResults(data);
            setFeatureSearchResults([]);
          } else {
            setGameSearchResults(data.games || []);
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
          }
          setShowGameSearch(true);
        }
      } catch (err) {
        console.error("Search failed:", err);
      }
    }, 200); // 200ms debounce
    
    setSearchDebounceTimer(timer);
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
          if (query.length >= 2) {
            handleGameSearch(query);
          } else {
            setShowGameSearch(false);
            setGameSearchResults([]);
            setFeatureSearchResults([]);
          }
          } else {
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

  const handleGameSelectFromMention = (game) => {
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

  const selectGame = (game) => {
    if (atMentionActive) {
      handleGameSelectFromMention(game);
    } else {
      // Add game to chips if not already present
      if (!gameChips.find(g => g.id === game.id)) {
        setGameChips([...gameChips, game]);
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
      const res = await fetch(`${API_BASE}/feedback/respond`, {
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
      const res = await fetch(`${API_BASE}/feedback/respond`, {
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
      
      const res = await fetch(`${API_BASE}/feedback/respond`, {
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

  const handleRequireFeature = (messageIndex, featureType, featureValue, autoRequery = true) => {
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
          const requiredArray = {};
          Object.keys(required).forEach(ft => {
            requiredArray[ft] = Array.from(required[ft]);
          });
          
          // Re-send the query with required features in context
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
          
          fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: {
              ...authService.getAuthHeaders(),
              "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
          })
          .then(res => res.json())
          .then(data => {
            
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
          })
          .catch(err => {
            console.error("Failed to re-query:", err);
            alert("Failed to update results. Please try again.");
          });
        }
      }
      
      return newRequired;
    });
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

  const sendMessage = async () => {
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
    
    // Allow sending if there's input OR if there are active required features
    if (!input.trim() && activeRequiredFeatures.length === 0) return;
    
    // If input is empty but we have required features, use a default message
    const messageText = input.trim() || (activeRequiredFeatures.length > 0 
      ? `Find games with ${activeRequiredFeatures.map(f => f.value).join(", ")}`
      : "");
    if (!messageText) return;

    const messageId = Date.now();
    const userMsg = { 
      role: "user", 
      text: messageText,
      messageId: messageId,
      status: "sending"
    };
    setMessages((prev) => [...prev, userMsg]);

    // Build context - include all feature information for feature-only searches
    const requiredFeatureValues = activeRequiredFeatures.length > 0 ? 
      activeRequiredFeatures.reduce((acc, f) => {
        if (!acc[f.type]) acc[f.type] = [];
        acc[f.type].push(f.value);
        return acc;
      }, {}) : undefined;
    
    const context = {
      last_game_id: gameChips.length > 0 ? gameChips[0].id : null,
      useCollection: useCollection,
      selected_game_id: gameChips.length > 0 ? gameChips[0].id : null,
      player_chips: playerChips,
      playtime_chips: playtimeChips.map(c => c.value),
      // Include required features from active required features
      required_feature_values: requiredFeatureValues,
    };
    
    // If useCollection is checked, explicitly set scope in message
    let finalMessageText = messageText;
    if (useCollection && !finalMessageText.toLowerCase().includes("in my collection") && !finalMessageText.toLowerCase().includes("my collection")) {
      finalMessageText = finalMessageText + " in my collection";
    }

    // Increment message count for anonymous users
    if (!user) {
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
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          ...authService.getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user?.id?.toString() || null,
          message: finalMessageText,
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
        };

        setMessages((prev) => [...prev, botMsg]);
      }
      
      // Request feedback question after response and attach to message
      if (user) {
        try {
          const feedbackRes = await fetch(`${API_BASE}/feedback/questions/random`, {
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
            >
              {showHistory ? "◀" : "▶"} History
            </button>
          </div>
        )}
        <div className="chat-window">
          <MessageList 
            messages={messages} 
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
            onLikeDislike={handleLikeDislike}
            onFeedbackResponse={handleFeedbackResponse}
            helpfulQuestion={helpfulQuestion}
            showDislikeInput={showDislikeInput}
            dislikeDetails={dislikeDetails}
            setDislikeDetails={setDislikeDetails}
            setShowDislikeInput={setShowDislikeInput}
            handleDislikeSubmit={handleDislikeSubmit}
            setMessages={setMessages}
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
          {/* Message limit warning for anonymous users */}
          {!user && messageLimitError && (
            <div className="message-limit-error" style={{
              padding: "0.75rem",
              marginBottom: "0.5rem",
              backgroundColor: "#ffebee",
              border: "1px solid #f44336",
              borderRadius: "4px",
              color: "#c62828"
            }}>
              {messageLimitError}
              <Link to="/login" style={{ marginLeft: "0.5rem", color: "#1976d2", textDecoration: "underline" }}>
                Log in to continue
              </Link>
            </div>
          )}
          {!user && !messageLimitError && (
            <div style={{
              padding: "0.5rem",
              marginBottom: "0.5rem",
              fontSize: "0.85rem",
              color: "#666",
              backgroundColor: "#f5f5f5",
              borderRadius: "4px"
            }}>
              {getRemainingMessages(5)} messages remaining today. <Link to="/login" style={{ color: "#1976d2", textDecoration: "underline" }}>Log in</Link> for unlimited messages.
            </div>
          )}
          {/* Processing indicator - only show after 5 seconds */}
          {isProcessing && showProcessingIndicator && (
            <div className="processing-indicator">
              Processing request...
            </div>
          )}
          
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
                        onClick={() => selectGame(game)}
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
            <div style={{ position: "relative", display: "flex", flexDirection: "column" }}>
              {activeRequiredFeatures.length > 0 && (
                <div style={{ marginBottom: "0.5rem", padding: "0.5rem", backgroundColor: "var(--bg-secondary, #f5f5f5)", borderRadius: "4px", fontSize: "0.9rem", minHeight: "2rem", border: "1px solid var(--border-color, #ddd)", display: "flex", alignItems: "center", flexWrap: "wrap", gap: "0.25rem" }}>
                  <span style={{ fontWeight: "bold", marginRight: "0.5rem" }}>Required features:</span>
                  <span style={{ display: "inline" }}>
                    {activeRequiredFeatures.map((feature, idx) => (
                      <span key={feature.key} style={{ display: "inline" }}>
                        {idx > 0 && <span style={{ margin: "0 0.25rem" }}>, </span>}
                        <span 
                          style={{ color: "#1976d2", cursor: "pointer", textDecoration: "underline" }} 
                          onClick={() => removeRequiredFeature(feature.key)} 
                          title="Click to remove"
                        >
                          {feature.type === "mechanics" && "⚙️ "}
                          {feature.type === "categories" && "🏷️ "}
                          {feature.type === "designers" && "👤 "}
                          {feature.type === "families" && "👨‍👩‍👧‍👦 "}
                          {feature.value}
                        </span>
                      </span>
                    ))}
                  </span>
                </div>
              )}
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", width: "100%" }}>
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
                    if (e.key === "Enter" && !atMentionActive && !isProcessing) {
                      sendMessage();
                    } else if (e.key === "Escape") {
                      setAtMentionActive(false);
                      setShowGameSearch(false);
                    }
                  }}
                  placeholder={gameChips.length > 0 ? `Ask about games similar to ${gameChips[0].name}...` : "Type @ to search for games, mechanics, categories, designers, or publishers"}
                  disabled={isProcessing}
                  style={{ flex: 1 }}
                />
                {/* Image upload button - requires game selection first */}
                <button
                  onClick={async () => {
                    // Check if game is selected
                    const lastGameId = gameChips.length > 0 ? gameChips[0].id : null;
                    const currentContext = input.trim() || null;
                    
                    if (!lastGameId) {
                      // Prompt user to select a game first
                      alert("Please select a game first using @ mention in the search box");
                      // Focus on input to help user
                      if (inputRef) {
                        inputRef.focus();
                      }
                      return;
                    }
                    
                    // Show fake-door message immediately (no file upload needed)
                    try {
                      const res = await fetch(`${API_BASE}/image/generate`, {
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
                          isFakeDoor: true, // Flag to hide like/dislike buttons
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
                  style={{ 
                    padding: "0.5rem", 
                    cursor: gameChips.length > 0 ? "pointer" : "not-allowed", 
                    border: "1px solid #ddd", 
                    borderRadius: "4px",
                    backgroundColor: gameChips.length > 0 ? "var(--bg-secondary, #f5f5f5)" : "var(--bg-disabled, #e0e0e0)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minWidth: "40px",
                    height: "40px",
                    opacity: gameChips.length > 0 ? 1 : 0.5
                  }}
                  title={gameChips.length > 0 ? "Upload image (coming soon)" : "Select a game first using @ mention"}
                  disabled={gameChips.length === 0}
                >
                  📷
                </button>
                {/* Rules explainer button */}
                <button
                  onClick={async () => {
                    // Get current game context
                    const lastGameId = gameChips.length > 0 ? gameChips[0].id : null;
                    const currentContext = input.trim() || null;
                    
                    if (!lastGameId) {
                      alert("Please select a game first to explain its rules");
                      return;
                    }
                    
                    try {
                      const res = await fetch(`${API_BASE}/rules/explain`, {
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
                          isFakeDoor: true, // Flag to hide like/dislike buttons
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
                  style={{ 
                    padding: "0.5rem", 
                    cursor: gameChips.length > 0 ? "pointer" : "not-allowed", 
                    border: "1px solid #ddd", 
                    borderRadius: "4px",
                    backgroundColor: gameChips.length > 0 ? "var(--bg-secondary, #f5f5f5)" : "var(--bg-disabled, #e0e0e0)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minWidth: "40px",
                    height: "40px",
                    opacity: gameChips.length > 0 ? 1 : 0.5
                  }}
                  title={gameChips.length > 0 ? "Explain rules (coming soon)" : "Select a game first"}
                  disabled={gameChips.length === 0}
                >
                  📖
                </button>
                {/* Scoring pad button */}
                <button
                  onClick={async () => {
                    // Get current game context
                    const lastGameId = gameChips.length > 0 ? gameChips[0].id : null;
                    const currentContext = input.trim() || null;
                    
                    if (!lastGameId) {
                      alert("Please select a game first to open scoring pad");
                      return;
                    }
                    
                    try {
                      const res = await fetch(`${API_BASE}/scoring/pad`, {
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
                        // Show fake-door message
                        alert(data.message);
                      } else if (data.exists && data.mechanism) {
                        // Open scoring pad component
                        setScoringPadGame({ id: lastGameId, name: gameChips[0].name, mechanism: data.mechanism });
                      } else {
                        alert("Scoring mechanism not available for this game yet.");
                      }
                    } catch (err) {
                      console.error("Scoring pad failed:", err);
                      alert("Failed to open scoring pad");
                    }
                  }}
                  style={{ 
                    padding: "0.5rem", 
                    cursor: gameChips.length > 0 ? "pointer" : "not-allowed", 
                    border: "1px solid #ddd", 
                    borderRadius: "4px",
                    backgroundColor: gameChips.length > 0 ? "var(--bg-secondary, #f5f5f5)" : "var(--bg-disabled, #e0e0e0)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minWidth: "40px",
                    height: "40px",
                    opacity: gameChips.length > 0 ? 1 : 0.5
                  }}
                  title={gameChips.length > 0 ? "End-game scoring pad" : "Select a game first using @ mention"}
                  disabled={gameChips.length === 0}
                >
                  📊
                </button>
              </div>
            </div>
            <button 
              onClick={sendMessage} 
              disabled={isProcessing || (!input.trim() && activeRequiredFeatures.length === 0)}
              title={isProcessing ? "Processing request..." : "Send message"}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minWidth: "40px",
                padding: "0.5rem"
              }}
            >
              {isProcessing ? "⏸️" : "📤"}
            </button>
          </div>
        </div>
      </div>
      
      {/* Feedback Question Modal */}
    </div>
  );
}

function MessageList({ messages, setMessages, onGameClick, user, onLikeDislike, onFeedbackResponse, helpfulQuestion, onRequireFeature, showDislikeInput, dislikeDetails, setDislikeDetails, setShowDislikeInput, handleDislikeSubmit }) {
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
            {m.abTest ? (
              <ABTestResults 
                abTest={m.abTest}
                onGameClick={onGameClick}
                onRequireFeature={onRequireFeature}
                messageIndex={idx}
                onFeedbackResponse={onFeedbackResponse}
              />
            ) : m.results && m.results.length > 0 && (
              <GameResultList 
                results={m.results} 
                onGameClick={onGameClick}
                onRequireFeature={onRequireFeature}
                messageIndex={idx}
                querySpec={m.querySpec}
              />
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

function GameResultList({ results, onGameClick, onRequireFeature, messageIndex, variant, differences, expandedGames, toggleExpand, querySpec }) {
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
                    style={{ cursor: "default" }}
                  >
                    {r.name || `Game ${r.game_id}`}
                  </div>
                  <div className="game-card__meta">
                    {r.designers && r.designers.length > 0 && (
                      <span style={{ marginRight: "1rem", fontSize: "0.9em", opacity: 0.8 }}>
                        👤 {r.designers.join(", ")}
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
                    <div className="shared-features-chips" style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.25rem", minHeight: "1.5rem" }}>
                      {sharedFeatures.length > 0 ? (
                        sharedFeatures.map((feature, idx) => (
                          <div 
                            key={`${feature.type}-${feature.value}-${idx}`}
                            className="shared-feature-chip"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onRequireFeature) {
                                onRequireFeature(messageIndex, feature.type, feature.value);
                              }
                            }}
                            title={`Click to require ${feature.value} (exclude games without this feature)`}
                            style={{
                              padding: "0.25rem 0.5rem",
                              backgroundColor: "var(--bg-secondary, #f5f5f5)",
                              border: "1px solid var(--border-color, #ddd)",
                              borderRadius: "4px",
                              cursor: "pointer",
                              fontSize: "0.85rem",
                              display: "flex",
                              alignItems: "center",
                              gap: "0.25rem"
                            }}
                          >
                            <span>{feature.value}</span>
                            <span className="shared-feature-chip-add" style={{ fontWeight: "bold", color: "#1976d2" }}>+</span>
                          </div>
                        ))
                      ) : (
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

function ABTestResults({ abTest, onGameClick, onRequireFeature, messageIndex, onFeedbackResponse }) {
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
