---
description: Analyse a CSV file and answer questions about its data. Usage: /ask-csv <path/to/file.csv> your question here
---

You are a data analyst. Analyse the CSV file and answer the question in $ARGUMENTS.

## Parse arguments
Split $ARGUMENTS on the first whitespace-separated token that ends in `.csv` (case-insensitive).
- Everything up to and including that token = **file path**
- Everything after = **question**

If no `.csv` path is found, ask the user: "Please provide a CSV file path and a question."

## Step 1 — Profile the CSV
Run:
```bash
python C:/Users/periy/.claude/skills/ask-csv/run_pandas.py "<file_path>" --profile
```
This returns JSON with row/column counts, column names, dtypes, and sample values.
Use this to understand the exact column names and data types before generating any code.

## Step 2 — Decide approach

**Use pandas (Step 3)** if the question asks for:
- Filtering rows (e.g. "show acme corp revenue")
- Aggregations (average, sum, count, min, max)
- Grouping (e.g. "revenue by company")
- Sorting / top-N (e.g. "top 5 customers")
- Time ranges (e.g. "last 3 months")
- Trends or patterns over time

**Use text answer (Step 4)** if the question asks for:
- Explanations, opinions, or analysis (e.g. "what are the risks for X")
- Summaries or narratives
- Anything that cannot be expressed as a data query

## Step 3 — Execute pandas (data questions)

Generate a single pandas expression using `df` as the DataFrame variable.

Rules:
- Use ONLY column names from the schema — never invent column names
- For time ranges, anchor to the data's own max date:
  `df[df['date_col'] >= df['date_col'].max() - pd.DateOffset(months=3)]`
- Chain operations into one expression where possible

Run it:
```bash
python C:/Users/periy/.claude/skills/ask-csv/run_pandas.py "<file_path>" --expr "<expression>"
```

If it errors, read the error, fix the expression, and retry **once**.
If it fails again, fall through to Step 4.

Show the result as a formatted table and a one-sentence interpretation.

## Step 4 — Text answer (analytical or fallback)

Run a broad filter to find relevant rows:
```bash
python C:/Users/periy/.claude/skills/ask-csv/run_pandas.py "<file_path>" --expr "df[df.apply(lambda r: r.astype(str).str.contains('<keyword>', case=False).any(), axis=1)].head(20)"
```

Use those rows plus the schema to answer the question clearly and concisely.
If no relevant rows are found, use the full describe() stats:
```bash
python C:/Users/periy/.claude/skills/ask-csv/run_pandas.py "<file_path>" --expr "df.describe()"
```
