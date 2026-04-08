import streamlit as st
import pandas as pd
import ollama
import re
import chardet

MODEL = "phi3:mini"

# -------------------------------
# INGESTION
# -------------------------------

def detect_encoding(file):
    raw = file.read(100000)
    file.seek(0)
    return chardet.detect(raw)["encoding"]

def robust_read_csv(file):
    enc = detect_encoding(file) or "utf-8"
    for e in [enc, "utf-8", "cp1252", "latin1"]:
        try:
            df = pd.read_csv(file, encoding=e)
            file.seek(0)
            return df
        except Exception:
            file.seek(0)
    raise ValueError("CSV load failed")

def profile_columns(df):
    profile = {}
    for col in df.columns:
        s = df[col]
        is_object = s.dtype == object
        cleaned = s.str.replace(r"[\$,£€%,\s]", "", regex=True).str.strip() if is_object else s
        profile[col] = {
            "numeric_pct": pd.to_numeric(cleaned, errors="coerce").notna().mean(),
            "date_pct": pd.to_datetime(s, errors="coerce").notna().mean() if is_object else 0.0,
        }
    return profile

def apply_types(df, profile):
    for col, meta in profile.items():
        if df[col].dtype != object:
            continue
        cleaned = df[col].str.replace(r"[\$,£€%,\s]", "", regex=True).str.strip()
        if meta["numeric_pct"] > 0.8:
            df[col] = pd.to_numeric(cleaned, errors="coerce")
        elif meta["date_pct"] > 0.8:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

@st.cache_data
def ingest_csv(file):
    df = robust_read_csv(file)
    df.columns = df.columns.str.strip().str.lower().str.replace(r"[^\w]+", "_", regex=True)
    profile = profile_columns(df)
    df = apply_types(df, profile)
    return df, profile

# -------------------------------
# PANDAS GENERATION
# -------------------------------

def build_schema(df):
    lines = []
    for col in df.columns:
        samples = df[col].dropna().head(3).tolist()
        lines.append(f"  {col} ({df[col].dtype}) — e.g. {', '.join(str(s) for s in samples)}")
    return "\n".join(lines)

def extract_pandas_expr(text):
    # Code block first
    match = re.search(r"```(?:python)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        lines = [l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
        return "\n".join(lines) if lines else None
    # Inline backtick
    match = re.search(r"`(df[^`\n]+)`", text)
    if match:
        return match.group(1).strip()
    # Bare df expression
    match = re.search(r"^(df[\s\S]+?)(?:\n\n|$)", text, re.MULTILINE)
    if match:
        lines = [l.strip() for l in match.group(1).splitlines() if l.strip() and not l.strip().startswith("#")]
        return "\n".join(lines) if lines else None
    return None

def generate_pandas_expr(question, df):
    schema = build_schema(df)
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    date_hint = (
        f"For time range questions, anchor to the data's own max date:\n"
        f"  df[df['{date_cols[0]}'] >= df['{date_cols[0]}'].max() - pd.DateOffset(months=3)]"
    ) if date_cols else ""

    prompt = f"""Convert this question to a pandas expression using a DataFrame called `df`.

Schema:
{schema}

Rules:
- If the question asks for data (filter, count, average, trend, top-N, group-by, time range) → return executable Python only, no explanation
- If the question asks for analysis, explanation, opinion, or cannot be answered by querying data → respond with exactly: NO_PANDAS
- Use only columns that exist in the schema above
- `df` is the only variable available
- For multi-step logic, use a single chained expression or multiple lines ending with the result
{date_hint}

Question: {question}"""

    res = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
    raw = res["message"]["content"].strip()
    if "NO_PANDAS" in raw.upper():
        return None
    return extract_pandas_expr(raw)

def run_pandas_expr(expr, df):
    result = eval(expr, {"df": df, "pd": pd}, {})  # noqa: S307
    if isinstance(result, pd.DataFrame):
        return result.reset_index(drop=True)
    if isinstance(result, pd.Series):
        return result.reset_index()
    return pd.DataFrame({"result": [result]})

def llm_repair_pandas(expr, error, df):
    schema = build_schema(df)
    prompt = f"""Fix this broken pandas expression.

DataFrame `df` schema:
{schema}

Broken expression:
{expr}

Error:
{error}

Return ONLY the fixed expression, no explanation."""

    res = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
    return extract_pandas_expr(res["message"]["content"])

# -------------------------------
# AGENT LOOP
# -------------------------------

def run_agent(question, df, step_callback):
    expr = generate_pandas_expr(question, df)

    # LLM signalled this needs a text answer, not a data query
    if expr is None:
        return None, None

    for i in range(3):
        step = {"iteration": i, "expr": expr}

        if not expr:
            step["status"] = "error"
            step["error"] = "No expression generated"
            step_callback(step)
            break

        try:
            result = run_pandas_expr(expr, df)
            step["status"] = "success"
            step_callback(step)
            return expr, result

        except Exception as e:
            err = str(e)
            step["status"] = "error"
            step["error"] = err
            step_callback(step)

            if i < 2:
                expr = llm_repair_pandas(expr, err, df)

    return None, None

# -------------------------------
# LLM FALLBACK
# -------------------------------

def stream_llm_fallback(question, df):
    keywords = [w for w in question.lower().split() if len(w) > 3]
    str_cols = df.select_dtypes(include="object")
    if keywords and not str_cols.empty:
        pattern = "|".join(re.escape(k) for k in keywords)
        mask = str_cols.apply(lambda col: col.str.contains(pattern, case=False, na=False)).any(axis=1)
        subset = df[mask].head(20) if mask.any() else df.head(10)
    else:
        subset = df.head(10)

    context = f"Stats:\n{df.describe().to_string()}\n\nRelevant rows:\n{subset.to_string()}"
    prompt = f"You are a data analyst.\n\nData:\n{context}\n\nAnswer clearly.\n\nQuestion: {question}"

    stream = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], stream=True)
    output = ""
    placeholder = st.empty()
    for chunk in stream:
        output += chunk["message"]["content"]
        placeholder.markdown(output)

# -------------------------------
# UI
# -------------------------------

st.title("📊 Self-Healing CSV Agent")

file = st.file_uploader("Upload CSV")

if file:
    df, profile = ingest_csv(file)
    st.dataframe(df.head())

    q = st.text_input("Ask a question")

    if q:
        st.markdown(f"### ❓ {q}")
        step_container = st.container()

        def stream_step(step):
            with step_container:
                st.markdown(f"**Iteration {step['iteration']}**")
                if step.get("expr"):
                    st.code(step["expr"], language="python")
                if step["status"] == "error":
                    st.error(step["error"])
                else:
                    st.success("✅ Success")

        with st.spinner("🧠 Thinking..."):
            expr, result = run_agent(q, df, stream_step)

        st.divider()

        if result is not None:
            st.subheader("📊 Result")
            st.dataframe(result)
        else:
            with st.status("🤔 Thinking...", expanded=True) as status:
                st.write("Pandas query couldn't answer this — analysing data directly...")
                stream_llm_fallback(q, df)
                status.update(label="💬 Answer ready", state="complete", expanded=True)
