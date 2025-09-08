# core/excel_parser.py
from __future__ import annotations
import pandas as pd

def sanitize_key(s: str) -> str:
    """Make a safe placeholder key (no spaces, slashes, etc.)."""
    return (
        str(s).strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("-", "_")
        .replace("(", "").replace(")", "")
        .replace(".", "_")
    )

def parse_excel_nodes(
    file, 
    sheet_name: str,
    node_col: str = "Node",
    x_col: str = "X",
    y_col: str = "Y",
    z_col: str = "Z",
    only_nodes: list[str] | None = None,
) -> dict:
    """
    Read a single sheet, return a flat dict of placeholders like:
      { "A1_X": 123.45, "A1_Y": 67.89, "A1_Z": -12.3, ... }
    """
    df = pd.read_excel(file, sheet_name=sheet_name, engine="openpyxl")
    # normalize headers (case-insensitive match)
    lower_map = {c.lower(): c for c in df.columns}
    def pick(col):
        if col in df.columns: return col
        key = col.lower()
        if key in lower_map: return lower_map[key]
        raise KeyError(f"Column '{col}' not found in sheet '{sheet_name}'. Found: {list(df.columns)}")
    node_col = pick(node_col); x_col = pick(x_col); y_col = pick(y_col); z_col = pick(z_col)

    # optional filtering to chosen nodes only
    if only_nodes:
        df = df[df[node_col].astype(str).isin(only_nodes)]

    out = {}
    for _, row in df.iterrows():
        node = sanitize_key(row[node_col])
        # skip blank node names
        if not node or str(node).lower() in ("nan", "none"):
            continue
        # make placeholders
        for label, col in (("X", x_col), ("Y", y_col), ("Z", z_col)):
            val = row[col]
            # leave as-is; Jinja will print numbers or strings fine
            out[f"{node}_{label}"] = None if pd.isna(val) else val
    return out

def list_sheet_names(file) -> list[str]:
    x = pd.ExcelFile(file, engine="openpyxl")
    return x.sheet_names
