# core/excel_parser.py (pure openpyxl)
from __future__ import annotations
from io import BytesIO
import re
from openpyxl import load_workbook

def sanitize_key(s: str) -> str:
    return (
        str(s).strip()
        .replace(" ", "_").replace("/", "_").replace("\\", "_")
        .replace("-", "_").replace("(", "").replace(")", "")
        .replace(".", "_")
    )

def list_sheet_names_bytes(file_bytes: bytes) -> list[str]:
    wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        return wb.sheetnames
    finally:
        wb.close()

_letter_re = re.compile(r"^[A-Za-z]+$")

def _col_letter_to_index(letter: str) -> int:
    """A→0, B→1, …, Z→25, AA→26, etc."""
    s = letter.strip().upper()
    idx = 0
    for ch in s:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1

def _resolve_column(ws, spec, has_header: bool) -> int:
    """
    spec can be:
      - column LETTER(s) like 'A'/'B'/'AA'  -> returns 0-based index
      - header name string (if has_header=True)
      - 1-based integer (1=A)
    """
    if isinstance(spec, int):
        return spec - 1
    s = str(spec).strip()
    # Column letters
    if _letter_re.match(s):
        return _col_letter_to_index(s)
    # Header name
    if has_header:
        # read first row values as headers
        headers = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
        lower_map = {h.lower(): i for i, h in enumerate(headers)}
        i = lower_map.get(s.lower())
        if i is None:
            raise KeyError(f"Header '{s}' not found. Available headers: {headers}")
        return i
    raise KeyError(f"Column '{s}' not found. Use letters (A,B,C,…) or enable 'has header'.")

def parse_excel_nodes_bytes(
    file_bytes: bytes,
    sheet_name: str,
    node_col: str | int = "Node",
    x_col: str | int = "X",
    y_col: str | int = "Y",
    z_col: str | int = "Z",
    only_nodes: list[str] | None = None,
    has_header: bool = True,
) -> dict:
    """
    Returns {'<Node>_X': val, '<Node>_Y': val, '<Node>_Z': val, ...}

    If has_header=False, the first row is data; column specs should be letters ('A','B','C','D') or 1-based ints.
    If has_header=True, you can use header names *or* letters/ints.
    """
    wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        if sheet_name not in wb.sheetnames:
            raise KeyError(f"Sheet '{sheet_name}' not found. Sheets: {wb.sheetnames}")
        ws = wb[sheet_name]

        # Resolve columns to 0-based indices
        i_node = _resolve_column(ws, node_col, has_header)
        i_x    = _resolve_column(ws, x_col,    has_header)
        i_y    = _resolve_column(ws, y_col,    has_header)
        i_z    = _resolve_column(ws, z_col,    has_header)

        # Start row: 2 if header, else 1
        start_row = 2 if has_header else 1

        out: dict[str, float | int | str | None] = {}
        seen: set[str] = set()
        only_set = set(str(n).strip() for n in only_nodes) if only_nodes else None

        for row in ws.iter_rows(min_row=start_row, values_only=True):
            # skip completely empty rows
            if row is None or all(v is None for v in row):
                continue

            try:
                raw_node = row[i_node]
            except IndexError:
                # fewer columns than expected
                continue

            if raw_node is None:
                continue

            node_name = str(raw_node).strip()
            if not node_name:
                continue
            if only_set and node_name not in only_set:
                continue

            key_base = sanitize_key(node_name)
            # avoid collisions on duplicate node names
            key = key_base
            k = 2
            while key in seen:
                key = f"{key_base}_{k}"
                k += 1
            seen.add(key)

            def _val(i):
                try:
                    return row[i]
                except IndexError:
                    return None

            out[f"{key}_X"] = _val(i_x)
            out[f"{key}_Y"] = _val(i_y)
            out[f"{key}_Z"] = _val(i_z)

        return out
    finally:
        wb.close()
