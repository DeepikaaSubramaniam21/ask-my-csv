# ask-my-csv

A local, offline CSV analyzer powered by [Ollama](https://ollama.com) and Phi-3 Mini. Upload any CSV file to explore its structure, generate an AI summary, and ask natural language questions about your data — no API keys required.

## Features

- **Structure view** — column names, data types, null counts, and sample values
- **Data preview** — random sample of up to 5 rows
- **AI summary** — one-click summary of what the dataset contains and notable patterns
- **Q&A** — ask any question about the data in plain English

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com) running locally with the `phi3:mini` model pulled

## Setup

```bash
# Install dependencies
pip install streamlit pandas ollama

# Pull the model
ollama pull phi3:mini

# Run the app
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

## Usage

1. Upload a `.csv` file using the file uploader
2. Review the structure and preview tables
3. Click **Summarize CSV** for an AI-generated overview
4. Type a question in the text box to query the data
