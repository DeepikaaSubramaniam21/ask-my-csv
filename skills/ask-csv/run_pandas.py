#!/usr/bin/env python3
"""
Helper for ask-csv skill.
  --profile            print schema JSON (columns, dtypes, samples)
  --expr "<expression>" evaluate a pandas expression against df
"""
import argparse
import json
import sys
import pandas as pd
import chardet


def detect_encoding(path):
    with open(path, "rb") as f:
        raw = f.read(100_000)
    return chardet.detect(raw)["encoding"] or "utf-8"


def load_csv(path):
    enc = detect_encoding(path)
    df = None
    for e in [enc, "utf-8", "cp1252", "latin1"]:
        try:
            df = pd.read_csv(path, encoding=e)
            break
        except Exception:
            continue
    if df is None:
        raise ValueError(f"Could not read {path}")

    df.columns = df.columns.str.strip().str.lower().str.replace(r"[^\w]+", "_", regex=True)

    for col in df.columns:
        s = df[col]
        if s.dtype != object:
            continue
        cleaned = s.str.replace(r"[\$,£€%,\s]", "", regex=True).str.strip()
        if pd.to_numeric(cleaned, errors="coerce").notna().mean() > 0.8:
            df[col] = pd.to_numeric(cleaned, errors="coerce")
        elif pd.to_datetime(s, errors="coerce").notna().mean() > 0.8:
            df[col] = pd.to_datetime(s, errors="coerce")

    return df


def cmd_profile(path):
    df = load_csv(path)
    schema = [
        {
            "column": col,
            "dtype": str(df[col].dtype),
            "samples": [str(s) for s in df[col].dropna().head(3).tolist()],
        }
        for col in df.columns
    ]
    print(json.dumps({"rows": len(df), "cols": len(df.columns), "schema": schema}, indent=2))


def cmd_run(path, expr):
    df = load_csv(path)
    result = eval(expr, {"df": df, "pd": pd}, {})  # noqa: S307
    if isinstance(result, pd.DataFrame):
        print(result.reset_index(drop=True).to_string())
    elif isinstance(result, pd.Series):
        print(result.reset_index().to_string())
    else:
        print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Path to CSV file")
    parser.add_argument("--profile", action="store_true", help="Print schema")
    parser.add_argument("--expr", help="Pandas expression to evaluate")
    args = parser.parse_args()

    if args.profile:
        cmd_profile(args.csv)
    elif args.expr:
        cmd_run(args.csv, args.expr)
    else:
        print("Provide --profile or --expr", file=sys.stderr)
        sys.exit(1)
