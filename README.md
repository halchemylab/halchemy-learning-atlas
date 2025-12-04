# Halchemy Library 📚

**Halchemy Library** is an AI-assisted reading path recommender designed for *learning*, not just reading. Unlike standard book search tools, it focuses on building a structured "curriculum" of 3–7 books to take you from beginner to competent in a specific domain.

It is built on a **curated dataset** (no AI hallucinations) and uses a deterministic sequencing engine to ensure logical progression (e.g., learning procedural skills in order of difficulty, or history chronologically).

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- [Streamlit](https://streamlit.io/)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/halchemy-library.git
   cd halchemy-library
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

Start the Streamlit application:
```bash
streamlit run app.py
```

The app will open in your default web browser at `http://localhost:8501`.

## 🧠 How It Works

The system uses a **Chat-to-Query** architecture:

1.  **Conversation:** A simple state machine collects your goals:
    *   **Topic:** (e.g., "I want to learn Python")
    *   **Level:** (Beginner / Intermediate / Advanced)
    *   **Style:** (Story-driven vs. Tactical/How-to)
    *   **Depth:** (Short path vs. Deep dive)
2.  **Filtering:** The engine queries `data/books.csv` to find matches.
3.  **Sequencing:** A Python-based sorter orders the books based on the learning type:
    *   *Procedural Skills* (coding, cooking) -> Sorted by Difficulty (1-5)
    *   *History* -> Sorted by Era/Chronology
    *   *Behavioral* (habits, leadership) -> Fundamentals -> Application
4.  **Hint Generation:** A rule-based helper provides domain-specific advice (e.g., "Practice code manually" for coding) to ensure skill adoption.

## 📂 Project Structure

```
.
├── app.py                 # Main Streamlit application entry point
├── requirements.txt       # Python dependencies
├── data/
│   └── books.csv          # The source of truth: curated book metadata
├── src/
│   └── books.py           # Logic for loading, filtering, and sequencing books
└── docs/
    └── book_data.md       # Guide on how to add books and manage metadata
```

## 🤝 Contributing

To add more books to the library, edit `data/books.csv`. Please read [docs/book_data.md](docs/book_data.md) for strict guidelines on metadata quality and verification to prevent "hallucinations."