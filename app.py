import streamlit as st
import pandas as pd
import ollama

st.set_page_config(page_title="CSV Analyzer", layout="wide")
st.title("📊 CSV Analyzer with Phi-3 Mini")

# File upload
uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Show structure
    st.subheader("📋 Structure")
    structure = pd.DataFrame({
        "Column": df.columns,
        "Type": df.dtypes.astype(str),
        "Non-Null": df.notnull().sum(),
        "Sample": [df[col].iloc[0] if len(df) > 0 else None for col in df.columns]
    })
    st.dataframe(structure, use_container_width=True)
    
    # Show preview
    st.subheader("👀 Preview")
    st.dataframe(df.sample(min(5, len(df))), use_container_width=True)
    
    # Generate summary
    if st.button("Summarize CSV"):
        with st.spinner("Analyzing..."):
            prompt = f"""Analyze this CSV data and provide a brief summary:

Columns: {list(df.columns)}
Shape: {df.shape[0]} rows, {df.shape[1]} columns
Data types: {df.dtypes.to_dict()}
Sample data:
{df.head(5).to_string()}

Provide a 3-4 sentence summary of what this data contains and any notable patterns."""

            response = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": prompt}]
            )
            st.success(response["message"]["content"])
    
    # Q&A
    st.subheader("💬 Ask a Question")
    question = st.text_input("Ask anything about the data:")
    
    if question:
        with st.spinner("Thinking..."):
            prompt = f"""You are a data analyst. Answer the question based on this CSV data.

Columns: {list(df.columns)}
Shape: {df.shape[0]} rows, {df.shape[1]} columns
Data types: {df.dtypes.to_dict()}
Statistics:
{df.describe().to_string()}

Sample data:
{df.head(10).to_string()}

Question: {question}

Answer concisely based on the data provided."""

            response = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": prompt}]
            )
            st.write(response["message"]["content"])