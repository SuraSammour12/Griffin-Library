# 📖 EverQuote — AI-Powered Reading Companion

> A semantic book recommender + personal reading tracker, built with sentence-transformers, FAISS, and Streamlit.

[![Streamlit App](https://img.shields.io/badge/streamlit-app-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-48%20passing-success)](#testing)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)

---

## ✨ What makes it different

Most reading apps are databases with checkboxes. EverQuote uses **semantic AI** at every layer:

🔭 **Search by feeling.** Describe a mood — "a quiet meditation on grief" — not keywords. The AI understands meaning via 768-dim sentence embeddings.

✨ **Personalized "For You".** Builds a taste vector from your rated books and surfaces matches you'll actually love. Uses **MMR re-ranking** for diversity.

🪶 **Semantic quote search.** Find that line you half-remember. "The part about courage and fear" — done.

🧠 **AI Insights.** Reading-DNA cards generated from your patterns: pace, taste signature, stalled books, eclectic palate.

🖼️ **Quote-to-image export.** Render any saved quote as a beautiful 1080×1080 PNG ready for sharing.

🔥 **Streaks & goals.** Light habit-loop layer to keep the reading momentum going.

---

## 🏗️ Architecture

```
everquote/
├── app.py                  ← Streamlit entry point
├── core/                   ← Pure business logic (no Streamlit)
│   ├── schemas.py          ← Pydantic models (type-safe data)
│   ├── storage.py          ← Atomic JSON writes + auto-backups
│   ├── library.py          ← Library service
│   ├── recommender.py      ← Hybrid scoring + MMR + explanations
│   ├── quote_search.py     ← Semantic search over user's quotes
│   ├── insights.py         ← AI-generated reading insights
│   ├── quote_image.py      ← PNG quote rendering
│   └── validation.py       ← Query sanity-checking
├── app/
│   ├── views/              ← Streamlit UI (one file per page)
│   └── styles/main.css     ← Production design system
├── tests/                  ← pytest suite (48 passing)
├── data/                   ← Runtime: library.json + backups/
└── models/                 ← Pre-built FAISS index + catalog
```

**Why this split?** The `core/` layer is pure Python — fully unit-testable, no Streamlit imports. The `app/` layer is just rendering. This means: tests run fast, business logic can be reused (CLI, API), and the codebase scales beyond a single-page demo.

---

## 🧠 The AI stack

| Component         | Tech                         | Why                                                  |
|-------------------|------------------------------|------------------------------------------------------|
| Embeddings        | `all-mpnet-base-v2`          | Strong semantic alignment, 768-d, fits in memory     |
| Vector index      | `FAISS` (flat L2)            | <100ms retrieval over 8.5K books                     |
| Hybrid scoring    | semantic + rating + popularity | Beats pure semantic for serendipity                  |
| Diversity         | **MMR re-ranking** (λ=0.75)  | Prevents 10 near-identical results                   |
| Explanations      | Concept extraction over catalog vocab | "Why this book?" surfaces matched themes |
| User profile      | Weighted-mean embedding      | rating/5 for finished, 0.5 for reading, 0.2 for want |

The recommender exposes three public methods:
- `search(query, …)` — semantic search with hybrid scoring + MMR
- `recommend_for_you(library)` — personalized picks from taste vector
- `all_genres()` — catalog vocabulary

Everything is decoupled from the UI and unit-testable.

---

## 🛡️ Production engineering

| Concern              | How it's solved                                    |
|----------------------|----------------------------------------------------|
| Data corruption      | Atomic writes (`tempfile` + `os.replace` + `fsync`) |
| Schema drift         | Pydantic validation on every load + auto-migration  |
| User data loss       | Daily rolling backups (last 7 kept) in `data/backups/` |
| Recovery             | Falls back to backups when main file is corrupted   |
| Salvage mode         | Drops invalid books, keeps the rest                 |
| Type safety          | Pydantic schemas for all persisted data             |
| Tests                | 48 passing (`pytest tests/ -v`)                     |
| Cold-start UX        | Cached `@st.cache_resource` for the model           |
| Graceful degradation | App still works if AI fails to load                 |

---

## 🚀 Getting started

### Prerequisites

- Python 3.10+
- `models/book_index.faiss` and `models/books_cleaned.pkl` (the pre-built FAISS index and catalog DataFrame)

### Install

```bash
git clone https://github.com/yourname/everquote.git
cd everquote
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

### Run tests

```bash
pytest tests/ -v
```

---

## 🌐 Deploy to Streamlit Cloud

1. Push the repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect the repo and set:
   - **Main file:** `app.py`
   - **Python version:** 3.10
4. Deploy.

The model files in `models/` are loaded once via `@st.cache_resource` so cold-start is the only slow page.

---

## 📊 What's worth highlighting

If you're skimming the code for the engineering bits:

- **`core/recommender.py`** — `_mmr_rerank`, `recommend_for_you`, `_explain_match`
- **`core/storage.py`** — atomic writes, backup rotation, schema migration
- **`core/quote_search.py`** — incremental embedding cache invalidation
- **`core/validation.py`** — fixed regex bug that rejected "strengths" / "rhythms"
- **`tests/test_validation.py`** — regression tests for the regex bug
- **`app/views/discover.py`** — AI-first UI with prominent match badges

---

## 📜 License

MIT — see [LICENSE](LICENSE).

---

Built with ☕ and curiosity.
