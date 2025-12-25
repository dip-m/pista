// frontend/src/utils/anonymousUser.js
// Utility for tracking anonymous users via browser fingerprinting

/**
 * Generate a simple browser fingerprint
 * Uses a combination of browser characteristics that are relatively stable
 */
export function getAnonymousUserId() {
  // Check if we already have an ID stored
  let anonymousId = localStorage.getItem('anonymous_user_id');
  
  if (!anonymousId) {
    // Generate a new ID based on browser characteristics
    const fingerprint = [
      navigator.userAgent,
      navigator.language,
      screen.width,
      screen.height,
      screen.colorDepth,
      new Date().getTimezoneOffset(),
      navigator.platform,
      navigator.hardwareConcurrency || 0,
      navigator.deviceMemory || 0,
    ].join('|');
    
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
      const char = fingerprint.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    
    anonymousId = `anon_${Math.abs(hash)}`;
    localStorage.setItem('anonymous_user_id', anonymousId);
  }
  
  return anonymousId;
}

/**
 * Get message count for today
 */
export function getTodayMessageCount() {
  const today = new Date().toDateString();
  const key = `message_count_${today}`;
  const count = localStorage.getItem(key);
  return count ? parseInt(count, 10) : 0;
}

/**
 * Increment message count for today
 */
export function incrementMessageCount() {
  const today = new Date().toDateString();
  const key = `message_count_${today}`;
  const count = getTodayMessageCount();
  localStorage.setItem(key, (count + 1).toString());
  return count + 1;
}

/**
 * Check if user has exceeded daily message limit
 */
export function hasExceededLimit(limit = 5) {
  return getTodayMessageCount() >= limit;
}

/**
 * Get remaining messages for today
 */
export function getRemainingMessages(limit = 5) {
  const count = getTodayMessageCount();
  return Math.max(0, limit - count);
}

