# ask-my-csv

A local, offline CSV analyzer powered by [Ollama](https://ollama.com) and Phi-3 Mini. Upload any CSV file to explore its structure, generate an AI summary, and ask natural language questions about your data — no API keys required.

## Features

- **Structure view** — column names, data types, null counts, and sample values
- **Data preview** — random sample of up to 5 rows
- **AI summary** — one-click summary of what the dataset contains and notable patterns
- **Q&A** — ask questions in plain English; answered via SQL execution or LLM fallback

## How Q&A Works

Questions are answered using a two-step pipeline for accuracy:

1. **SQL path** — the LLM generates a DuckDB SQL query, validated and repaired by [sqlglot](https://github.com/tobymao/sqlglot) before execution. Results are exact and deterministic.
2. **Fallback path** — if the question can't be expressed as SQL (e.g. "what patterns do you see?"), it falls back to LLM-over-data with streaming output.

A debug panel on each response shows which path was taken, the raw LLM output, and any SQL repairs applied.

## Choosing a Model

This app runs **fully offline** using [Ollama](https://ollama.com) — no API keys, no internet required. Pick a model based on your machine's available RAM.

A range of Gemma, Qwen, and Phi models are available. As a rule of thumb, you need roughly 1.5–2× the model's parameter size in free RAM (e.g. a 4B model needs ~6–8GB).

### Quick Comparison

| Model | Parameters | Good For | Accuracy | Ollama tag |
|---|---|---|---|---|
| Gemma 3 1B | 1B | Speed, edge devices (≥2GB RAM) | ❌ Poor | `gemma3:1b` |
| Gemma 3 4B | 4B | Balance (≥6GB RAM) | ⚠️ Okay | `gemma3:4b` |
| Gemma 3 27B | 27B | Quality (≥32GB RAM) | ✅ Good | `gemma3:27b` |
| Phi-3 Mini | 3.8B | Balance, low memory (≥4GB RAM) | ⚠️ Okay | `phi3:mini` |
| Phi-3 Medium | 14B | Quality (≥16GB RAM) | ✅ Good | `phi3:medium` |
| Qwen2.5 3B | 3B | Speed, multilingual (≥4GB RAM) | ⚠️ Okay | `qwen2.5:3b` |
| Qwen2.5 7B | 7B | Balance, multilingual (≥8GB RAM) | ✅ Good | `qwen2.5:7b` |
| Gemini 1.5 Flash | — | Speed + quality | ✅ Good | ☁️ Cloud |
| Gemini 1.5 Pro | — | Best quality | ✅✅ Great | ☁️ Cloud |
| Claude Sonnet | — | Quality | ✅✅ Great | ☁️ Cloud |

> **Note:** Gemini and Claude are cloud-based models and require API keys. All others run fully offline via Ollama.

To swap models, update the `MODEL` constant at the top of `app.py` and pull the model:

```bash
ollama pull gemma3:4b   # example
```

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com) running locally with your chosen model pulled

## Setup

```bash
# Install dependencies
pip install streamlit pandas ollama duckdb sqlglot

# Pull a model (example — pick one from the table above)
ollama pull phi3:mini

# Run the app
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

## Usage

1. Upload a `.csv` file using the file uploader
2. Review the structure and preview tables
3. Click **Summarize CSV** for an AI-generated overview
4. Type a question — the app will execute SQL where possible, fall back to LLM otherwise
