from src.books import load_books, filter_books, sequence_books, get_hint_for_category

def test_logic():
    print("Loading books...")
    df = load_books()
    print(f"Loaded {len(df)} books.")
    
    print("\n--- Test 1: Habits (Beginner, Short) ---")
    filtered = filter_books(df, category="habits", level="beginner")
    sequenced = sequence_books(filtered, depth="short")
    print(f"Found {len(sequenced)} books:")
    for _, row in sequenced.iterrows():
        print(f"- {row['title']} (Diff: {row['difficulty']})")
        
    print("\n--- Test 2: Python (Intermediate, Deep) ---")
    filtered = filter_books(df, category="coding", subcategory="python", level="intermediate")
    sequenced = sequence_books(filtered, depth="deep")
    print(f"Found {len(sequenced)} books:")
    for _, row in sequenced.iterrows():
        print(f"- {row['title']} (Diff: {row['difficulty']})")

    print(f"\nHint for 'habits': {get_hint_for_category('habits')}")

if __name__ == "__main__":
    test_logic()
