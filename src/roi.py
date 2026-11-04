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
            if not isinstance(data, dict):
                return DEFAULT_STATS.copy()
            return {
                key: data[key] if type(data.get(key)) is int and data[key] >= 0 else default
                for key, default in DEFAULT_STATS.items()
            }
    except (ValueError, IOError):
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
