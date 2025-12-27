#!/usr/bin/env python3
"""
Script to deduce the "feel" of a game by analyzing forum discussions.
Summarizes forum opinions, posts, comments, and responses.
Stores keywords with weight/embeddings.
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import Counter
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import DB_PATH
from backend.logger_config import logger

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")


def clean_text(text: str) -> str:
    """Clean HTML and normalize text."""
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode HTML entities (basic)
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract meaningful keywords from text."""
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its',
        'our', 'their', 'what', 'which', 'who', 'whom', 'whose', 'where',
        'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'just', 'now', 'then', 'here',
        'there', 'when', 'where', 'why', 'how', 'game', 'games', 'play',
        'playing', 'played', 'player', 'players'
    }

    # Extract words (alphanumeric, at least min_length chars)
    words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + r',}\b', text.lower())

    # Filter stop words and return unique words
    keywords = [w for w in words if w not in stop_words and len(w) >= min_length]

    return list(set(keywords))


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Simple sentiment analysis (positive/negative/neutral)."""
    positive_words = {
        'love', 'great', 'excellent', 'amazing', 'fantastic', 'wonderful',
        'awesome', 'brilliant', 'perfect', 'best', 'favorite', 'enjoy',
        'fun', 'enjoyable', 'satisfying', 'engaging', 'immersive'
    }

    negative_words = {
        'hate', 'terrible', 'awful', 'bad', 'worst', 'boring', 'dull',
        'disappointing', 'frustrating', 'confusing', 'broken', 'flawed',
        'overrated', 'underwhelming', 'tedious', 'repetitive'
    }

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        sentiment = 'positive'
        score = positive_count / (positive_count + negative_count + 1)
    elif negative_count > positive_count:
        sentiment = 'negative'
        score = negative_count / (positive_count + negative_count + 1)
    else:
        sentiment = 'neutral'
        score = 0.5

    return {
        'sentiment': sentiment,
        'score': score,
        'positive_words': positive_count,
        'negative_words': negative_count
    }


def process_forum_data(forum_dir: Path) -> Dict[str, Any]:
    """Process all forum data from a directory."""
    all_texts = []
    all_keywords = []
    sentiments = []

    # Load forums
    forums_file = forum_dir / "forums.json"
    if not forums_file.exists():
        logger.warning(f"Forums.json not found in {forum_dir}")
        return {}

    with open(forums_file, 'r', encoding='utf-8') as f:
        forums = json.load(f)

    # Process each forum
    for forum in forums:
        forum_id = forum['id']
        forum_title = forum['title']

        # Find forum directory
        forum_dirs = list(forum_dir.glob(f"forum_{forum_id}_*"))
        if not forum_dirs:
            continue

        forum_path = forum_dirs[0]

        # Load threads
        threads_file = forum_path / "threads.json"
        if not threads_file.exists():
            continue

        with open(threads_file, 'r', encoding='utf-8') as f:
            threads = json.load(f)

        # Process each thread
        for thread in threads:
            thread_id = thread['id']
            thread_files = list(forum_path.glob(f"thread_{thread_id}_*.json"))

            for thread_file in thread_files:
                with open(thread_file, 'r', encoding='utf-8') as f:
                    thread_data = json.load(f)

                # Process articles
                for article in thread_data.get('articles', []):
                    body = clean_text(article.get('body', ''))
                    if not body or len(body) < 20:  # Skip very short posts
                        continue

                    all_texts.append(body)
                    keywords = extract_keywords(body)
                    all_keywords.extend(keywords)

                    sentiment = analyze_sentiment(body)
                    sentiments.append(sentiment)

    # Aggregate results
    keyword_counts = Counter(all_keywords)
    top_keywords = keyword_counts.most_common(100)

    # Calculate average sentiment
    if sentiments:
        avg_sentiment_score = sum(s['score'] for s in sentiments) / len(sentiments)
        positive_count = sum(1 for s in sentiments if s['sentiment'] == 'positive')
        negative_count = sum(1 for s in sentiments if s['sentiment'] == 'negative')
        neutral_count = sum(1 for s in sentiments if s['sentiment'] == 'neutral')

        dominant_sentiment = 'positive' if positive_count > negative_count else ('negative' if negative_count > positive_count else 'neutral')
    else:
        avg_sentiment_score = 0.5
        positive_count = negative_count = neutral_count = 0
        dominant_sentiment = 'neutral'

    return {
        'total_posts': len(all_texts),
        'total_keywords': len(set(all_keywords)),
        'top_keywords': [{'keyword': k, 'count': c} for k, c in top_keywords],
        'sentiment': {
            'dominant': dominant_sentiment,
            'score': avg_sentiment_score,
            'positive_posts': positive_count,
            'negative_posts': negative_count,
            'neutral_posts': neutral_count,
            'total_sentiment_analyzed': len(sentiments)
        }
    }


def generate_embeddings(keywords: List[str], model=None) -> Dict[str, List[float]]:
    """Generate embeddings for keywords."""
    if not HAS_TRANSFORMERS:
        logger.warning("sentence-transformers not available, skipping embeddings")
        return {}

    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')

    embeddings = {}
    for keyword in keywords:
        embedding = model.encode(keyword, convert_to_numpy=True)
        embeddings[keyword] = embedding.tolist()

    return embeddings


def deduce_game_feel(game_id: int, forums_dir: str = "gen/forums") -> Dict[str, Any]:
    """Deduce game feel from forum discussions."""
    forum_dir = Path(forums_dir) / f"game_{game_id}"

    if not forum_dir.exists():
        logger.error(f"Forum directory not found: {forum_dir}")
        return {}

    logger.info(f"Analyzing forum data for game {game_id}")

    # Process forum data
    analysis = process_forum_data(forum_dir)

    if not analysis:
        logger.warning(f"No forum data found for game {game_id}")
        return {}

    # Generate embeddings for top keywords
    top_keywords = [kw['keyword'] for kw in analysis['top_keywords'][:50]]
    embeddings = generate_embeddings(top_keywords)

    # Add embeddings to keywords
    for kw_data in analysis['top_keywords']:
        keyword = kw_data['keyword']
        if keyword in embeddings:
            kw_data['embedding'] = embeddings[keyword]
            kw_data['embedding_dim'] = len(embeddings[keyword])

    # Create summary
    summary = {
        'game_id': game_id,
        'analysis': analysis,
        'summary_text': f"Based on {analysis['total_posts']} forum posts, the game has a {analysis['sentiment']['dominant']} sentiment "
                       f"(score: {analysis['sentiment']['score']:.2f}). "
                       f"Top keywords include: {', '.join([kw['keyword'] for kw in analysis['top_keywords'][:10]])}."
    }

    return summary


def save_game_feel(game_id: int, feel_data: Dict[str, Any], conn: sqlite3.Connection):
    """Save game feel data to database."""
    # Create table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS game_feel (
            game_id INTEGER PRIMARY KEY,
            summary_text TEXT,
            sentiment_dominant TEXT,
            sentiment_score REAL,
            positive_posts INTEGER,
            negative_posts INTEGER,
            neutral_posts INTEGER,
            total_posts INTEGER,
            keywords_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)

    analysis = feel_data.get('analysis', {})
    sentiment = analysis.get('sentiment', {})
    keywords = analysis.get('top_keywords', [])

    conn.execute("""
        INSERT OR REPLACE INTO game_feel
        (game_id, summary_text, sentiment_dominant, sentiment_score,
         positive_posts, negative_posts, neutral_posts, total_posts, keywords_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game_id,
        feel_data.get('summary_text', ''),
        sentiment.get('dominant', 'neutral'),
        sentiment.get('score', 0.5),
        sentiment.get('positive_posts', 0),
        sentiment.get('negative_posts', 0),
        sentiment.get('neutral_posts', 0),
        analysis.get('total_posts', 0),
        json.dumps(keywords)
    ))

    conn.commit()
    logger.info(f"Saved game feel data for game {game_id}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Deduce game feel from forum discussions")
    parser.add_argument("game_id", type=int, help="BGG game ID")
    parser.add_argument("--forums-dir", default="gen/forums", help="Forums directory (default: gen/forums)")
    parser.add_argument("--save-db", action="store_true", help="Save results to database")

    args = parser.parse_args()

    feel_data = deduce_game_feel(args.game_id, args.forums_dir)

    if feel_data:
        print(json.dumps(feel_data, indent=2, ensure_ascii=False))

        if args.save_db:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            save_game_feel(args.game_id, feel_data, conn)
            conn.close()
    else:
        logger.error("Failed to deduce game feel")


if __name__ == "__main__":
    main()
