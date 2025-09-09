# core/excel_parser.py
from __future__ import annotations
import pandas as pd
from io import BytesIO

def sanitize_key(s: str) -> str:
    """Make a safe placeholder key (no spaces/punct)."""
    return (
        str(s).strip()
        .replace(" ", "_").replace("/", "_").replace("\\", "_")
        .replace("-", "_").replace("(", "").replace(")", "")
        .replace(".", "_")
    )

def _pick_column(df: pd.DataFrame, name_or_aliases) -> str:
    """
    Find a column by exact name (case sensitive), case-insensitive, or any alias.
    name_or_aliases can be a str or list[str].
    """
    if isinstance(name_or_aliases, str):
        aliases = [name_or_aliases]
    else:
        aliases = list(name_or_aliases)

    # exact first
    for a in aliases:
        if a in df.columns:
            return a

    # case-insensitive fallback
    lower_map = {c.lower(): c for c in df.columns}
    for a in aliases:
        c = lower_map.get(a.lower())
        if c:
            return c

    raise KeyError(
        f"None of the expected columns {aliases} found. Available: {list(df.columns)}"
    )

def list_sheet_names_bytes(file_bytes: bytes) -> list[str]:
    bio = BytesIO(file_bytes)
    x = pd.ExcelFile(bio, engine="openpyxl")
    return x.sheet_names

def parse_excel_nodes_bytes(
    file_bytes: bytes,
    sheet_name: str,
    node_col: str | list[str] = "Node",
    x_col: str | list[str] = "X",
    y_col: str | list[str] = "Y",
    z_col: str | list[str] = "Z",
    only_nodes: list[str] | None = None,
) -> dict:
    """
    Read one sheet and return placeholders like:
      { "A1_X": 123.45, "A1_Y": 67.89, "A1_Z": -12.3, ... }

    - node_col/x_col/y_col/z_col can be a string OR a list of aliases.
    - only_nodes allows filtering to a subset (match on the raw node cell string).
    """
    bio = BytesIO(file_bytes)
    df = pd.read_excel(bio, sheet_name=sheet_name, engine="openpyxl")

    # pick columns robustly
    node_col = _pick_column(df, node_col)
    x_col    = _pick_column(df, x_col)
    y_col    = _pick_column(df, y_col)
    z_col    = _pick_column(df, z_col)

    # optional filtering
    if only_nodes:
        only = set(str(n).strip() for n in only_nodes)
        df = df[df[node_col].astype(str).str.strip().isin(only)]

    out: dict[str, float | int | str | None] = {}
    seen: set[str] = set()

    for _, row in df.iterrows():
        raw_node = row[node_col]
        node = sanitize_key(raw_node)
        if not node or node.lower() in ("nan", "none"):
            continue

        # If duplicate node names exist, suffix with an index (A1, A1_2, …)
        base = node
        idx = 2
        while node in seen:
            node = f"{base}_{idx}"
            idx += 1
        seen.add(node)

        # capture XYZ (don’t force float; keep ints/strings as-is)
        for lbl, col in (("X", x_col), ("Y", y_col), ("Z", z_col)):
            val = row[col]
            out[f"{node}_{lbl}"] = None if pd.isna(val) else val

    return out
