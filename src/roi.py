import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
STATS_FILE = os.path.join(DATA_DIR, 'roi_stats.json')

DEFAULT_STATS = {
    "usage_count": 0,
    "time_saved_mins": 0,
    "money_saved_usd": 0
}

def load_stats():
    """Loads ROI stats from the JSON file."""
    if not os.path.exists(STATS_FILE):
        return DEFAULT_STATS.copy()
    
    try:
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_STATS.copy()

def increment_stats(time_saved=15, money_saved=10):
    """Increments usage and savings stats, then saves to file."""
    stats = load_stats()
    
    stats["usage_count"] += 1
    stats["time_saved_mins"] += time_saved
    stats["money_saved_usd"] += money_saved
    
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)
    except IOError:
        pass # Fail silently in production if we can't write
        
    return stats
