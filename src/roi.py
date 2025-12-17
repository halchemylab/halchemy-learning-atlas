import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
STATS_FILE = os.path.join(DATA_DIR, 'roi_stats.json')

DEFAULT_STATS = {
    "paths_generated": 0,
    "books_recommended": 0
}

def load_stats():
    """Loads Library stats from the JSON file."""
    if not os.path.exists(STATS_FILE):
        return DEFAULT_STATS.copy()
    
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            # Basic schema check/migration
            if "paths_generated" not in data:
                 return DEFAULT_STATS.copy()
            # Remove 'topics_explored' if it exists from previous runs
            if "topics_explored" in data:
                del data["topics_explored"]
            return data
    except (json.JSONDecodeError, IOError):
        return DEFAULT_STATS.copy()

def increment_stats(num_books=0, category=None):
    """Increments library stats and saves to file."""
    stats = load_stats()
    
    stats["paths_generated"] += 1
    stats["books_recommended"] += num_books
    
    # 'topics_explored' logic removed
    
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
    except IOError:
        pass 
        
    return stats

