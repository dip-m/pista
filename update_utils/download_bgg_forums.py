#!/usr/bin/env python3
"""
Script to download BGG forum discussions for a game.
Saves forum posts, comments, and responses to a folder structure.
"""
import os
import sys
import json
import time
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import requests
from xml.etree import ElementTree as ET

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import DB_PATH
from backend.logger_config import logger


def get_forum_list(game_id: int) -> List[Dict[str, Any]]:
    """Get list of forums for a game."""
    url = f"https://www.boardgamegeek.com/xmlapi2/forumlist?type=thing&id={game_id}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        forums = []
        for forum in root.findall(".//forum"):
            forums.append({
                "id": forum.get("id"),
                "title": forum.get("title"),
                "numthreads": int(forum.get("numthreads", 0)),
                "numposts": int(forum.get("numposts", 0)),
            })
        
        return forums
    except Exception as e:
        logger.error(f"Error fetching forum list for game {game_id}: {e}")
        return []


def get_forum_threads(forum_id: int, page: int = 1) -> List[Dict[str, Any]]:
    """Get threads from a forum."""
    url = f"https://www.boardgamegeek.com/xmlapi2/forum?type=thing&id={forum_id}&page={page}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        threads = []
        for thread in root.findall(".//thread"):
            threads.append({
                "id": thread.get("id"),
                "subject": thread.get("subject"),
                "author": thread.get("author"),
                "numarticles": int(thread.get("numarticles", 0)),
                "postdate": thread.get("postdate"),
                "lastpostdate": thread.get("lastpostdate"),
            })
        
        return threads
    except Exception as e:
        logger.error(f"Error fetching threads for forum {forum_id}: {e}")
        return []


def get_thread_articles(thread_id: int, page: int = 1) -> List[Dict[str, Any]]:
    """Get articles (posts/comments) from a thread."""
    url = f"https://www.boardgamegeek.com/xmlapi2/thread?id={thread_id}&page={page}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        articles = []
        for article in root.findall(".//article"):
            body_elem = article.find("body")
            body = body_elem.text if body_elem is not None else ""
            
            articles.append({
                "id": article.get("id"),
                "subject": article.get("subject"),
                "author": article.get("username"),
                "postdate": article.get("postdate"),
                "editdate": article.get("editdate"),
                "numedits": int(article.get("numedits", 0)),
                "body": body,
            })
        
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles for thread {thread_id}: {e}")
        return []


def download_game_forums(game_id: int, output_dir: str, max_forums: int = None, max_threads_per_forum: int = 10):
    """Download all forums for a game and save to folder structure."""
    output_path = Path(output_dir) / f"game_{game_id}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Downloading forums for game {game_id} to {output_path}")
    
    # Get forum list
    forums = get_forum_list(game_id)
    if not forums:
        logger.warning(f"No forums found for game {game_id}")
        return
    
    if max_forums:
        forums = forums[:max_forums]
    
    logger.info(f"Found {len(forums)} forums")
    
    # Save forum list
    with open(output_path / "forums.json", "w", encoding="utf-8") as f:
        json.dump(forums, f, indent=2, ensure_ascii=False)
    
    # Download each forum
    for forum in forums:
        forum_id = forum["id"]
        forum_title = forum["title"].replace("/", "_").replace("\\", "_")
        forum_dir = output_path / f"forum_{forum_id}_{forum_title}"
        forum_dir.mkdir(exist_ok=True)
        
        logger.info(f"Downloading forum: {forum_title} ({forum_id})")
        
        # Get threads
        threads = get_forum_threads(forum_id, page=1)
        if max_threads_per_forum:
            threads = threads[:max_threads_per_forum]
        
        logger.info(f"Found {len(threads)} threads in forum {forum_id}")
        
        # Save threads list
        with open(forum_dir / "threads.json", "w", encoding="utf-8") as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        
        # Download each thread
        for thread in threads:
            thread_id = thread["id"]
            thread_subject = thread["subject"].replace("/", "_").replace("\\", "_")
            thread_file = forum_dir / f"thread_{thread_id}_{thread_subject}.json"
            
            logger.info(f"Downloading thread: {thread_subject} ({thread_id})")
            
            # Get articles
            articles = []
            page = 1
            while True:
                page_articles = get_thread_articles(thread_id, page=page)
                if not page_articles:
                    break
                articles.extend(page_articles)
                if len(page_articles) < 50:  # BGG returns 50 per page
                    break
                page += 1
                time.sleep(1)  # Rate limiting
            
            thread_data = {
                "thread_info": thread,
                "articles": articles,
            }
            
            with open(thread_file, "w", encoding="utf-8") as f:
                json.dump(thread_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(articles)} articles from thread {thread_id}")
            time.sleep(1)  # Rate limiting
        
        time.sleep(2)  # Rate limiting between forums
    
    logger.info(f"Download complete. Forums saved to {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download BGG forum discussions for a game")
    parser.add_argument("game_id", type=int, help="BGG game ID")
    parser.add_argument("--output-dir", default="gen/forums", help="Output directory (default: gen/forums)")
    parser.add_argument("--max-forums", type=int, help="Maximum number of forums to download")
    parser.add_argument("--max-threads", type=int, default=10, help="Maximum threads per forum (default: 10)")
    
    args = parser.parse_args()
    
    download_game_forums(
        args.game_id,
        args.output_dir,
        max_forums=args.max_forums,
        max_threads_per_forum=args.max_threads
    )


if __name__ == "__main__":
    main()

