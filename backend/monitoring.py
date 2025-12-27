"""
Monitoring and alerting utilities for silent failures and errors.
"""
import time
from typing import Dict, Any, Optional
from collections import defaultdict
import json

from backend.logger_config import logger

# In-memory error tracking (for simple monitoring)
_error_counts = defaultdict(int)
_error_timestamps = defaultdict(list)
_last_alert_time = {}

# Configuration
ALERT_THRESHOLD = 5  # Number of errors before alerting
ALERT_WINDOW_SECONDS = 60  # Time window for error counting
ALERT_COOLDOWN_SECONDS = 300  # Don't alert more than once per 5 minutes


def record_error(error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
    """
    Record an error for monitoring.

    Args:
        error_type: Type of error (e.g., "database_connection", "query_failure")
        error_message: Error message
        context: Additional context about the error
    """
    timestamp = time.time()
    key = f"{error_type}:{error_message[:50]}"  # Truncate message for grouping

    _error_counts[key] += 1
    _error_timestamps[key].append(timestamp)

    # Clean old timestamps (outside alert window)
    cutoff = timestamp - ALERT_WINDOW_SECONDS
    _error_timestamps[key] = [ts for ts in _error_timestamps[key] if ts > cutoff]
    _error_counts[key] = len(_error_timestamps[key])

    # Check if we should alert
    if _error_counts[key] >= ALERT_THRESHOLD:
        last_alert = _last_alert_time.get(key, 0)
        if timestamp - last_alert > ALERT_COOLDOWN_SECONDS:
            _last_alert_time[key] = timestamp
            send_alert(error_type, error_message, _error_counts[key], context)

    # Log the error
    log_data = {
        "error_type": error_type,
        "error_message": error_message,
        "count": _error_counts[key],
        "context": context or {},
    }
    logger.error(f"MONITORING: {json.dumps(log_data)}")


def send_alert(error_type: str, error_message: str, count: int, context: Optional[Dict[str, Any]] = None):
    """
    Send an alert for repeated errors.
    This can be extended to send emails, Slack messages, etc.
    """
    alert_message = f"ALERT: {error_type} - {error_message} (occurred {count} times in last {ALERT_WINDOW_SECONDS}s)"
    if context:
        alert_message += f" | Context: {json.dumps(context)}"

    logger.critical(alert_message)

    # TODO: Add external alerting (email, Slack, PagerDuty, etc.)
    # For now, just log critically
    # Example:
    # send_slack_message(alert_message)
    # send_email(to="admin@example.com", subject="Pista Error Alert", body=alert_message)


def get_error_stats() -> Dict[str, Any]:
    """Get current error statistics for monitoring dashboard."""
    current_time = time.time()
    cutoff = current_time - ALERT_WINDOW_SECONDS

    stats = {"total_errors": sum(_error_counts.values()), "error_types": {}, "recent_errors": []}

    for key, count in _error_counts.items():
        recent_timestamps = [ts for ts in _error_timestamps[key] if ts > cutoff]
        if recent_timestamps:
            error_type = key.split(":")[0]
            if error_type not in stats["error_types"]:
                stats["error_types"][error_type] = 0
            stats["error_types"][error_type] += len(recent_timestamps)

            stats["recent_errors"].append(
                {"key": key, "count": len(recent_timestamps), "last_occurrence": max(recent_timestamps)}
            )

    return stats


def reset_error_counts():
    """Reset error counts (useful for testing or manual reset)."""
    global _error_counts, _error_timestamps, _last_alert_time
    _error_counts.clear()
    _error_timestamps.clear()
    _last_alert_time.clear()
