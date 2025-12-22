# Halchemy Library 📚

**Halchemy Library** is an AI-assisted reading path recommender designed for *learning*, not just reading. Unlike standard book search tools, it focuses on building a structured "curriculum" of 3–7 books to take you from beginner to competent in a specific domain.

It combines a **curated dataset** (to prevent AI hallucinations) with a **deterministic sequencing engine** and **LLM intelligence** (GPT-4) to provide personalized, logical learning journeys.

## ✨ Key Features

- **AI Librarian (Chat-to-Query):** Interactive chat interface that translates your learning goals into structured queries.
- **Visual Roadmaps:** Automatic generation of learning maps using Graphviz to visualize your progression.
- **Deterministic Sequencing:** Logic-based ordering of books (e.g., Procedural skills by difficulty, History chronologically).
- **Expert Rationales:** AI-generated explanations of *why* each book was chosen for your specific path.
- **Multiple Exports:** Download your curated curriculum as a clean Markdown file or a professional PDF.
- **Library Stats:** Track your learning ROI with metrics on generated paths and recommended books.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- [Graphviz](https://graphviz.org/download/) (required for visual roadmaps)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/halchemy-library.git
   cd halchemy-library
   ```

2. **Set up Environment Variables:**
   Copy the example environment file and add your OpenAI API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Create a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies:**
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

The system uses a **Hybrid Architecture**:

1.  **Conversation:** An LLM processes your intent and extracts parameters (Topic, Level, Style, Depth).
2.  **Filtering:** The engine queries `data/books.csv` to find matches from a curated source.
3.  **Sequencing:** A Python-based sorter orders the books based on the learning type (Procedural, History, or Behavioral).
4.  **Rationale & Hints:** The LLM analyzes the selected books to provide a custom rationale and domain-specific advice.

## 🧪 Testing

The project includes a comprehensive test suite covering data validation and recommendation logic.

Run tests using:
```bash
python -m unittest discover tests
```

## 📂 Project Structure

```
.
├── app.py                 # Main Streamlit application
├── data/
│   ├── books.csv          # Curated book metadata (Source of Truth)
│   └── roi_stats.json     # Tracking for library metrics
├── src/
│   ├── books.py           # Filtering and sequencing logic
│   ├── llm_client.py      # OpenAI integration
│   ├── pdf_gen.py         # PDF report generation logic
│   ├── roi.py             # Stats tracking and ROI logic
│   └── utils.py           # Utility functions (e.g., cover fetching)
├── tests/                 # Unit and integration tests
└── docs/
    └── book_data.md       # Guidelines for managing book metadata
```

## 🤝 Contributing

To add more books to the library, edit `data/books.csv`. Please read [docs/book_data.md](docs/book_data.md) for strict guidelines on metadata quality and verification to prevent "hallucinations."
