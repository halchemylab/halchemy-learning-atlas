import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
STATS_FILE = os.path.join(DATA_DIR, 'roi_stats.json')

DEFAULT_STATS = {
    "paths_generated": 0,
    "books_recommended": 0,
    "topics_explored": []
}

def load_stats():
    """Loads Library stats from the JSON file."""
    if not os.path.exists(STATS_FILE):
        return DEFAULT_STATS.copy()
    
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            # Basic schema check/migration - if old schema or missing keys, reset or adapt
            if "paths_generated" not in data:
                 return DEFAULT_STATS.copy()
            return data
    except (json.JSONDecodeError, IOError):
        return DEFAULT_STATS.copy()

def increment_stats(num_books=0, category=None):
    """Increments library stats and saves to file."""
    stats = load_stats()
    
    stats["paths_generated"] += 1
    stats["books_recommended"] += num_books
    
    if category:
        # Normalize category to lowercase for consistency
        cat_lower = category.lower()
        if cat_lower not in stats["topics_explored"]:
            stats["topics_explored"].append(cat_lower)
    
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
    except IOError:
        pass 
        
    return stats

