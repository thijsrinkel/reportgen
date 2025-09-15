# app/streamlit_app.py
from pathlib import Path
import sys
from io import BytesIO
import zipfile
import json, yaml
import streamlit as st

# ---------- PATH FIX (must be first) ----------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ---------------------------------------------

st.set_page_config(page_title="Caisson Reports", layout="centered")
st.image("img/TM Edison.png", width=300)
st.title("MOG 2 MCR & DIMCON Report Generator")

# ---------- SAFE IMPORTS ----------
imports_ok = {}
try:
    from core.renderer import render_all_to_memory
    imports_ok["core.renderer"] = True
except Exception as e:
    imports_ok["core.renderer"] = e

excel_ready = True
try:
    from core.excel_parser import list_sheet_names_bytes, parse_excel_two_blocks_bytes
    imports_ok["core.excel_parser"] = True
except Exception as e:
    imports_ok["core.excel_parser"] = e
    excel_ready = False
# ----------------------------------

SPECS_DIR = ROOT / "template_specs"

# ---------------- Excel upload ----------------
st.subheader("Excel")
uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

excel_vals = st.session_state.setdefault("excel_vals", {})
excel_bytes = st.session_state.get("excel_bytes")

if uploaded:
    excel_bytes = uploaded.getvalue()
    st.session_state["excel_bytes"] = excel_bytes

if excel_bytes and excel_ready:
    try:
        sheets = list_sheet_names_bytes(excel_bytes)
        sheet = st.selectbox("Choose sheet", sheets, key="sheet_pick")

        with st.expander("Column settings", expanded=False):
            st.caption("Caisson Offsets (A–D): Node + XYZ")
            c1, c2, c3, c4 = st.columns(4)
            with c1: left_node_col = st.text_input("Node col", value="A")
            with c2: left_x_col    = st.text_input("X col",    value="B")
            with c3: left_y_col    = st.text_input("Y col",    value="C")
            with c4: left_z_col    = st.text_input("Z col",    value="D")
            left_has_header = st.checkbox("Has header row", value=True)

            st.caption("Seiral Numbers and Document References (I–J): Placeholder → Value")
            c5, c6 = st.columns(2)
            with c5: right_key_col = st.text_input("Key col",   value="I")
            with c6: right_val_col = st.text_input("Value col", value="J")
            right_has_header = st.checkbox("Has header row", value=True)

            only_nodes_text = st.text_input("Only include these LEFT node names (comma-separated)", value="")
            only_nodes = [s.strip() for s in only_nodes_text.split(",") if s.strip()] or None

        if st.button("Parse Excel"):
            excel_vals = parse_excel_two_blocks_bytes(
                excel_bytes,
                sheet_name=sheet,
                left_node_col=left_node_col,
                left_x_col=left_x_col,
                left_y_col=left_y_col,
                left_z_col=left_z_col,
                left_has_header=left_has_header,
                right_key_col=right_key_col,
                right_val_col=right_val_col,
                right_has_header=right_has_header,
                only_nodes=only_nodes,
            )
            st.session_state["excel_vals"] = excel_vals
            st.success(f"Parsed {len(excel_vals)} placeholders from '{sheet}'.")

            # ---- Full viewer ----
            all_items = sorted(excel_vals.items(), key=lambda kv: kv[0])
            st.caption(f"{len(all_items)} placeholders loaded.")
            q = st.text_input("Filter placeholders", value="")
            if q:
                ql = q.lower()
                view = [kv for kv in all_items if ql in kv[0].lower()]
            else:
                view = all_items

            rows = [{"placeholder": k, "value": v} for k, v in view]
            st.dataframe(rows, hide_index=True, use_container_width=True)

            with st.expander("All names (copy/paste)"):
                st.text_area("Names", "\n".join(k for k, _ in view), height=300)

            st.download_button(
                "Download placeholders as JSON",
                data=json.dumps(dict(all_items), indent=2, ensure_ascii=False, default=str),
                file_name="excel_placeholders.json",
            )
            st.download_button(
                "Download placeholders as YAML",
                data=yaml.safe_dump(dict(all_items), sort_keys=True, allow_unicode=True),
                file_name="excel_placeholders.yaml",
            )
    except Exception as e:
        st.error(f"Excel error: {e}")
elif not excel_ready:
    st.info("Excel parsing not available. Check core/excel_parser.py and requirements.")
else:
    st.caption("Upload an .xlsx file to enable parsing.")

# ---------------- Render & Download ----------------
st.divider()
if st.button("Render reports"):
    try:
        context = dict(st.session_state.get("excel_vals", {}))  # all from Excel
        if not context:
            raise ValueError("No placeholders parsed yet. Click 'Parse Excel' first.")
        outputs = render_all_to_memory(context, SPECS_DIR)
        st.session_state["rendered"] = outputs
        st.success(f"Generated {len(outputs)} report(s).")
    except Exception as e:
        st.error(f"Render failed: {e}")
        import traceback
        st.code("".join(traceback.format_exc()))

rendered = st.session_state.get("rendered", {})
if rendered:
    st.subheader("Download")
    for fname, blob in rendered.items():
        name = Path(fname).name
        st.download_button(f"Download {name}", data=blob, file_name=name)
    if len(rendered) > 1:
        zbuf = BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, blob in rendered.items():
                zf.writestr(Path(fname).name, blob)
        st.download_button("Download ALL as ZIP", data=zbuf.getvalue(), file_name="reports.zip", mime="application/zip")

# ---------------- Debug ----------------
with st.expander("Debug"):
    st.write("Imports:", {k: (True if v is True else f"{type(v).__name__}: {v}") for k, v in imports_ok.items()})
    st.write("Excel bytes present:", st.session_state.get("excel_bytes") is not None)
    st.write("Parsed placeholders:", len(st.session_state.get("excel_vals", {})))
