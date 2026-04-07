import streamlit as st
import pandas as pd
import ollama
import duckdb
import re
import sqlglot
import sqlglot.expressions as exp

MODEL = "phi3:mini"
DIALECT = "duckdb"
STAT_KEYWORDS = {"average", "mean", "max", "min", "sum", "count", "median", "std", "total"}
MAX_HISTORY = 50

_SQL_PATTERNS = [
    re.compile(r"```(?:sql)?\s*(SELECT[\s\S]+?)```", re.IGNORECASE),
    re.compile(r"(SELECT[\s\S]+?;)", re.IGNORECASE),
    re.compile(r"(SELECT[\s\S]+)", re.IGNORECASE),
]

st.set_page_config(page_title="CSV Analyzer", layout="wide")
st.title("📊 CSV Analyzer with Phi-3 Mini")

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    for col in df.select_dtypes(include="object").columns:
        cleaned = df[col].str.replace(r"[\$,£€%]", "", regex=True).str.strip()
        coerced = pd.to_numeric(cleaned, errors="coerce")
        if coerced.notna().sum() / max(len(df), 1) >= 0.8:
            df[col] = coerced
    stats = df.describe().to_string()
    return df, stats

def stream_response(prompt, spinner_text):
    with st.spinner(spinner_text):
        stream = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        output = ""
        with st.empty():
            for chunk in stream:
                output += chunk["message"]["content"]
                st.write(output)
    return output

def extract_sql(text):
    for pattern in _SQL_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None

def validate_and_repair_sql(sql, col_map, varchar_cols):
    try:
        tree = sqlglot.parse_one(sql, dialect=DIALECT)
    except sqlglot.errors.ParseError as e:
        return None, f"Parse error: {e}"

    for col_node in tree.find_all(exp.Column):
        name_lower = col_node.name.lower()
        if name_lower in col_map:
            actual = col_map[name_lower]
            col_node.set("this", exp.Identifier(this=actual, quoted=" " in actual))

    for agg_node in tree.find_all(exp.Avg, exp.Sum, exp.Min, exp.Max, exp.Stddev, exp.Variance):
        for col_node in agg_node.find_all(exp.Column):
            if col_node.name.lower() in varchar_cols:
                col_node.replace(exp.TryCast(
                    this=col_node.copy(),
                    to=exp.DataType(this=exp.DataType.Type.DOUBLE)
                ))

    return tree.sql(dialect=DIALECT), None

def try_sql(question, con, schema, col_map, varchar_cols):
    sql_prompt = f"""You are a SQL expert. Convert the question into a DuckDB SQL query against a table called "df".

Table schema:
{schema}

Rules:
- Return ONLY the SQL query, nothing else
- If the question cannot be expressed as SQL, respond with exactly: NO_SQL
- Use single quotes for string values e.g. WHERE Department = 'Engineering'
- Use double quotes only for column names that contain spaces e.g. "First Name"

Question: {question}"""

    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": sql_prompt}])
    raw = response["message"]["content"].strip()
    debug = {"llm_raw": raw, "sql": None, "repaired_sql": None, "error": None, "path": None}

    def fail(path, error=None):
        debug["path"] = path
        debug["error"] = error
        return None, None, debug

    if "NO_SQL" in raw.upper():
        return fail("no_sql")

    sql = extract_sql(raw) or (raw if raw.upper().startswith("SELECT") else None)
    debug["sql"] = sql
    if not sql:
        return fail("extract_failed")

    repaired_sql, parse_error = validate_and_repair_sql(sql, col_map, varchar_cols)
    if parse_error:
        return fail("parse_failed", parse_error)

    debug["repaired_sql"] = repaired_sql
    try:
        result = con.execute(repaired_sql).df()
        debug["path"] = "sql_success"
        return repaired_sql, result, debug
    except Exception as e:
        return fail("exec_failed", str(e))

def render_sql_result(result):
    if result.shape == (1, 1):
        st.metric(label=result.columns[0], value=result.iloc[0, 0])
    elif result.shape[0] == 1:
        for col in result.columns:
            st.markdown(f"**{col}:** {result.iloc[0][col]}")
    else:
        for _, row in result.iterrows():
            st.markdown("- " + " | ".join(f"**{col}:** {row[col]}" for col in result.columns))

uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    df, cached_stats = load_data(uploaded_file)

    # Precompute schema metadata once per file
    col_map = {c.lower(): c for c in df.columns}
    varchar_cols = {c.lower() for c in df.select_dtypes(include="object").columns}
    schema = "\n".join(f"  {col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes))
    compact_context = f"Columns and types:\n{df.dtypes.to_string()}\n\nSample data (3 rows):\n{df.head(3).to_string()}"

    # Cache duckdb connection and df registration per file
    if st.session_state.get("df_id") != id(df):
        con = duckdb.connect()
        con.register("df", df)
        st.session_state.db_conn = con
        st.session_state.df_id = id(df)
    con = st.session_state.db_conn

    st.subheader("📋 Structure")
    structure = pd.DataFrame({
        "Column": df.columns,
        "Type": df.dtypes.astype(str),
        "Non-Null": df.notnull().sum(),
        "Sample": [str(df[col].iloc[0]) if len(df) > 0 else "" for col in df.columns]
    })
    st.dataframe(structure, width="stretch")

    st.subheader("👀 Preview")
    st.dataframe(df.sample(min(5, len(df))), width="stretch")

    if st.button("Summarize CSV"):
        prompt = f"""Analyze this CSV data and provide a brief summary:

Shape: {df.shape[0]} rows, {df.shape[1]} columns
{compact_context}

Provide a 3-4 sentence summary of what this data contains and any notable patterns."""
        stream_response(prompt, "Analyzing...")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("💬 Ask a Question")

    for entry in st.session_state.chat_history:
        st.markdown(f"**Q:** {entry['question']}")
        if entry.get("sql"):
            st.code(entry["sql"], language="sql")
        st.markdown(f"**A:** {entry['answer']}")
        st.divider()

    question = st.text_input("Ask anything about the data:", key="question_input")

    if question:
        with st.spinner("Thinking..."):
            sql, sql_result, debug = try_sql(question, con, schema, col_map, varchar_cols)

        with st.expander("🔍 Debug", expanded=False):
            st.write(f"**Path taken:** `{debug['path']}`")
            st.write("**LLM raw output:**")
            st.code(debug["llm_raw"])
            if debug["sql"]:
                st.write("**Extracted SQL:**")
                st.code(debug["sql"], language="sql")
            if debug["repaired_sql"] and debug["repaired_sql"] != debug["sql"]:
                st.write("**Repaired SQL (sqlglot):**")
                st.code(debug["repaired_sql"], language="sql")
            if debug["error"]:
                st.error(f"Error: {debug['error']}")

        if sql is not None and sql_result is not None:
            st.code(sql, language="sql")
            render_sql_result(sql_result)
            answer = sql_result.to_string(index=False)
        else:
            context = compact_context
            if any(word in question.lower() for word in STAT_KEYWORDS):
                context += f"\n\nStatistics:\n{cached_stats}"
            prompt = f"""You are a data analyst. Answer the question based on this CSV data.

Shape: {df.shape[0]} rows, {df.shape[1]} columns
{context}

Question: {question}

Answer concisely based on the data provided."""
            answer = stream_response(prompt, "Thinking...")

        history = st.session_state.chat_history
        history.append({"question": question, "sql": sql, "answer": answer})
        if len(history) > MAX_HISTORY:
            st.session_state.chat_history = history[-MAX_HISTORY:]
