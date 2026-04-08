# ask-my-csv

A local, offline CSV analyzer powered by [Ollama](https://ollama.com) and Phi-3 Mini. Upload any CSV file, ask questions in plain English, and get accurate answers — no API keys, no internet required.

## Features

- **Structure view** — column names, data types, null counts, and sample values
- **Data preview** — random sample of rows on load
- **Q&A** — ask anything about your data; answered via pandas execution or LLM text fallback

## How Q&A Works

Questions are answered using a two-layer pipeline:

### Layer 1 — LLM → Pandas (data questions)
For questions that can be answered by querying the data ("average revenue by company", "top 5 customers last 3 months", "show acme corp revenue over time"), the LLM generates a pandas expression which is executed directly against the DataFrame.

- No SQL dialect issues — pandas handles mixed types natively
- Up to 3 attempts: initial generation + one LLM repair if execution fails
- Each attempt is shown as an iteration with the expression and any error

### Layer 2 — LLM text answer (analytical questions)
If the LLM signals the question can't be answered by querying data (e.g. "what are the risks for unity partners?", "explain the trend"), it falls straight through to a text answer using relevant rows from the dataset as context.

A `NO_PANDAS` escape hatch prevents the LLM from forcing analytical questions into code.

## Choosing a Model

This app runs **fully offline** using [Ollama](https://ollama.com). Pick a model based on your machine's available RAM.

As a rule of thumb, you need roughly 1.5–2× the model's parameter size in free RAM (e.g. a 4B model needs ~6–8GB).

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

## Use as a Claude Code Skill

Prefer working in the terminal? The same functionality is available as a [Claude Code](https://claude.ai/code) skill — no browser, no Streamlit server, no Ollama required. Claude itself generates and runs the pandas code.

### How it differs from the Streamlit app

| | Streamlit app | Claude skill |
|---|---|---|
| Interface | Browser | Claude Code CLI |
| LLM | Local (Ollama + phi3:mini) | Claude (Sonnet/Opus) |
| Repair loop | 3 iterations | Not needed |
| Dependencies | streamlit, ollama, chardet | pandas, chardet |

### Installation

**1. Create the skill directory**

macOS/Linux:
```bash
mkdir -p ~/.claude/skills/ask-csv
```

Windows:
```powershell
mkdir "$env:USERPROFILE\.claude\skills\ask-csv"
```

**2. Copy the skill files**

```bash
# from the ask-my-csv repo root
cp skills/ask-csv/SKILL.md ~/.claude/skills/ask-csv/
cp skills/ask-csv/run_pandas.py ~/.claude/skills/ask-csv/
```

**3. Update the path in `SKILL.md`**

Open `~/.claude/skills/ask-csv/SKILL.md` and replace the hardcoded path with your own:

```
# find and replace this:
C:/Users/periy/.claude/skills/ask-csv/run_pandas.py

# with your home directory path, e.g.:
/Users/yourname/.claude/skills/ask-csv/run_pandas.py   # macOS/Linux
C:/Users/yourname/.claude/skills/ask-csv/run_pandas.py # Windows
```

**4. Install the dependency**

```bash
pip install pandas chardet
```

**5. Restart Claude Code** to pick up the new skill.

### Usage

Inside Claude Code, type:

```
/ask-csv path/to/your.csv give me revenue by company
/ask-csv path/to/your.csv top 5 customers last 3 months
/ask-csv path/to/your.csv what are the risks for unity partners
```

Data questions (filter, aggregate, group-by, trends) run as pandas and return a result table. Analytical questions get a text answer using relevant rows as context.

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com) running locally with your chosen model pulled

## Setup

```bash
# Install dependencies
pip install streamlit pandas ollama chardet

# Pull a model (example — pick one from the table above)
ollama pull phi3:mini

# Run the app
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

## Usage

1. Upload a `.csv` file
2. Review the data preview
3. Type a question — data questions execute as pandas, analytical questions get a text answer
