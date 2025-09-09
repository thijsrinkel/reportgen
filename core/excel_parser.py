from openpyxl import load_workbook
from io import BytesIO

def parse_excel_nodes_bytes(file_bytes: bytes, sheet_name: str) -> dict:
    wb = load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb[sheet_name]

    out = {}
    # assume first row is headers
    headers = [str(c.value).strip() for c in next(ws.iter_rows(min_row=1, max_row=1))]
    col_map = {h.lower(): i for i, h in enumerate(headers)}

    def col_index(name):
        for k,v in col_map.items():
            if k == name.lower():
                return v
        raise KeyError(f"Column {name} not found in {headers}")

    node_col = col_index("Node")
    x_col    = col_index("X")
    y_col    = col_index("Y")
    z_col    = col_index("Z")

    for row in ws.iter_rows(min_row=2):  # skip header
        node = str(row[node_col].value).strip()
        if not node or node.lower() in ("none","nan"):
            continue
        out[f"{node}_X"] = row[x_col].value
        out[f"{node}_Y"] = row[y_col].value
        out[f"{node}_Z"] = row[z_col].value

    return out
