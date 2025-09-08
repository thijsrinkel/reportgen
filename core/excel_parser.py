# core/excel_parser.py
from __future__ import annotations
import pandas as pd
from io import BytesIO

def sanitize_key(s: str) -> str:
    return (
        str(s).strip()
        .replace(" ", "_").replace("/", "_").replace("\\", "_")
        .replace("-", "_").replace("(", "").replace(")", "")
        .replace(".", "_")
    )

def list_sheet_names_bytes(file_bytes: bytes) -> list[str]:
    bio = BytesIO(file_bytes)
    x = pd.ExcelFile(bio, engine="openpyxl")
    return x.sheet_names

def parse_excel_nodes_bytes(
    file_bytes: bytes,
    sheet_name: str,
    node_col: str = "Node",
    x_col: str = "X", y_col: str = "Y", z_col: str = "Z",
    only_nodes: list[str] | None = None,
) -> dict:
    bio = BytesIO(file_bytes)
    df = pd.read_excel(bio, sheet_name=sheet_name, engine="openpyxl")

    lower_map = {c.lower(): c for c in df.columns}
    def pick(col):
        if col in df.columns: return col
        if col.lower() in lower_map: return lower_map[col.lower()]
        raise KeyError(f"Column '{col}' not found; got {list(df.columns)}")

    node_col = pick(node_col); x_col = pick(x_col); y_col = pick(y_col); z_col = pick(z_col)
    if only_nodes:
        df = df[df[node_col].astype(str).isin(only_nodes)]

    out = {}
    for _, row in df.iterrows():
        node = sanitize_key(row[node_col])
        if not node or str(node).lower() in ("nan", "none"): continue
        for lbl, col in (("X", x_col), ("Y", y_col), ("Z", z_col)):
            val = row[col]
            out[f"{node}_{lbl}"] = None if pd.isna(val) else val
    return out
