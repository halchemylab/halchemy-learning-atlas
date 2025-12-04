# Book Data Curation Guide

This document explains how to maintain and extend the `data/books.csv` dataset for Halchemy Library. The integrity of this file is critical—the app relies 100% on this data and does not use generative AI to invent book titles.

## 1. The Data Schema

The `books.csv` file is a standard CSV with the following columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | Unique identifier for the book. |
| `title` | String | Full title of the book. |
| `author` | String | Author name(s). |
| `category` | String | Broad topic (e.g., `coding`, `history`, `cooking`). |
| `subcategory` | String | Specific niche (e.g., `python`, `WWII`, `japanese-cooking`). Optional. |
| `difficulty` | 1-5 | 1 = Absolute Beginner, 5 = Expert/Academic. |
| `readability` | 1-5 | 5 = Page-turner, 1 = Dense textbook. Avoid books < 3 for beginners. |
| `style` | String | `tactical/how-to`, `story-driven`, `academic`, `reference`. |
| `learning_type` | String | Used for sorting. `procedural-skill`, `narrative-history`, `behavioral-skill`, `conceptual`. |
| `chronology_hint` | Mixed | Year (e.g., `1945`) or Era (`Ancient`). Used to sort history books. |
| `short_description` | String | 1-2 sentences explaining *why* this book helps learn the topic. |
| `store_url` | URL | Link to buy the book (Amazon, Bookshop.org, etc.). |
| `affiliate_url` | URL | Your monetized link (can be placeholder for now). |
| `is_beginner_friendly` | Boolean | `TRUE` if appropriate for total novices. |
| `is_intermediate` | Boolean | `TRUE` if appropriate for someone with basics. |
| `is_advanced` | Boolean | `TRUE` if appropriate for experts. |

## 2. How to Add a Book

1.  **Verify Existence:** Ensure the book exists and is highly rated. Do not guess details.
2.  **Determine Metadata:**
    *   **Difficulty:** Skim the table of contents. Does it assume prior knowledge?
    *   **Style:** Is it a biography (`story-driven`) or a manual (`tactical`)?
3.  **Write Description:** Write a custom description focused on *learning utility*.
    *   *Bad:* "Published in 2018 by O'Reilly."
    *   *Good:* "Teaches the fundamentals of memory management in Rust through hands-on examples."
4.  **Update CSV:** Add a new row to `data/books.csv`. ensure you **quote** fields that contain commas (like descriptions).

## 3. Using Gemini CLI for Curation

You can use the Gemini CLI to *brainstorm* candidates, but **you must manually verify** the output.

**Example Prompt:**
> "List 5 seminal books on 'User Experience Design' sorted from beginner to advanced. For each, provide a 1-sentence description of what skill it teaches."

**Verification Step:**
Take the output and check Amazon/Goodreads to confirm:
1.  The title and author are correct.
2.  The edition is current.
3.  The "difficulty" matches reality.

## 4. Affiliate Links

Currently, the `affiliate_url` column contains placeholders (`TODO...`).
To monetize:
1.  Sign up for Amazon Associates or a similar program.
2.  Generate links for each `store_url`.
3.  Batch update the CSV with the real links.
