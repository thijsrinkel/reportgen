# app/streamlit_app.py
from pathlib import Path
import sys
from io import BytesIO
import zipfile
import streamlit as st

# ---------- PATH FIX (must be first) ----------
ROOT = Path(__file__).resolve().parents[1]  # repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ---------------------------------------------

st.set_page_config(page_title="Caisson Reports", layout="centered")
st.title("Caisson Reports")

# ---------- SAFE IMPORTS ----------
imports_ok = {}
try:
    from pydantic import ValidationError
    imports_ok["pydantic"] = True
except Exception as e:
    imports_ok["pydantic"] = e

try:
    from jinja2.exceptions import UndefinedError
    imports_ok["jinja2"] = True
except Exception as e:
    imports_ok["jinja2"] = e

try:
    from core.models import JobData
    imports_ok["core.models"] = True
except Exception as e:
    imports_ok["core.models"] = e

try:
    from core.renderer import render_all_to_memory
    imports_ok["core.renderer"] = True
except Exception as e:
    imports_ok["core.renderer"] = e

# Excel is optional: app must still render without it
excel_ready = True
try:
    from core.excel_parser import list_sheet_names_bytes, parse_excel_nodes_bytes
    imports_ok["core.excel_parser"] = True
except Exception as e:
    imports_ok["core.excel_parser"] = e
    excel_ready = False
# ----------------------------------

SPECS_DIR = ROOT / "template_specs"

# ---------------- Excel (optional) ----------------
st.subheader("Excel nodes (optional)")
uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

# Show a quick smoke test so you know if Excel libs work
if uploaded:
    try:
        import pandas as pd
        from io import BytesIO as _BytesIO
        xls = pd.ExcelFile(_BytesIO(uploaded.getvalue()), engine="openpyxl")
        st.caption("Excel OK. Sheets: " + ", ".join(xls.sheet_names))
    except Exception as e:
        st.warning(f"Excel smoke test failed: {e}")

excel_vals = st.session_state.setdefault("excel_vals", {})
excel_bytes = st.session_state.get("excel_bytes")

if uploaded:
    excel_bytes = uploaded.getvalue()
    st.session_state["excel_bytes"] = excel_bytes

if excel_bytes and excel_ready:
    try:
        # simple (no caching) to minimize moving parts while we debug UI
        sheets = list_sheet_names_bytes(excel_bytes)
        sheet = st.selectbox("Choose sheet", sheets, key="sheet_pick")

        with st.expander("Columns (change if headers differ)", expanded=False):
            node_col = st.text_input("Node column", value="Node")
            x_col    = st.text_input("X column", value="X")
            y_col    = st.text_input("Y column", value="Y")
            z_col    = st.text_input("Z column", value="Z")

        filter_text = st.text_input("Only include these node names (comma separated)", value="")
        only_nodes = [s.strip() for s in filter_text.split(",") if s.strip()] or None

        if st.button("Load nodes from Excel"):
            excel_vals = parse_excel_nodes_bytes(
                excel_bytes, sheet,
                node_col=node_col, x_col=x_col, y_col=y_col, z_col=z_col,
                only_nodes=only_nodes
            )
            st.session_state["excel_vals"] = excel_vals
            st.success(f"Loaded {len(excel_vals)} placeholders from '{sheet}'.")
            if excel_vals:
                st.caption("Preview (first 12):")
                st.code(", ".join(sorted(excel_vals.keys())[:12]))
    except Exception as e:
        st.error(f"Excel error: {e}")
elif not excel_ready:
    st.info("Excel parsing not available. You can still fill the form and render reports.")
else:
    st.caption("Upload an .xlsx file to enable node import.")
# --------------------------------------------------

# ---------------- Form (always render) ----------------
data = st.session_state.setdefault("data", {})
defaults = {
    "CaissonNumber": "",
    "IP_1": "", "IP_2": "",
    "SN_SBG1": "", "SN_Septentrio1": "", "SN_Ant1": "", "SN_Ant2": "",
    "SN_SBG2": "", "SN_Septentrio2": "", "SN_Ant3": "", "SN_Ant4": "",
    "MCRDocumentReference": "", "DIMCONDocumentReference": "",
    "DocumentReference8": "", "DocumentReference9": "",
}
for k, v in defaults.items():
    data.setdefault(k, v)

with st.form("job-form"):
    st.subheader("Caisson & System IDs")
    data["CaissonNumber"] = st.text_input("CaissonNumber", value=data.get("CaissonNumber",""))

    c1, c2 = st.columns(2)
    with c1:
        data["IP_1"] = st.text_input("IP_1", value=data.get("IP_1",""))
        data["SN_SBG1"] = st.text_input("SN_SBG1", value=data.get("SN_SBG1",""))
        data["SN_Septentrio1"] = st.text_input("SN_Septentrio1", value=data.get("SN_Septentrio1",""))
        data["SN_Ant1"] = st.text_input("SN_Ant1", value=data.get("SN_Ant1",""))
        data["SN_Ant2"] = st.text_input("SN_Ant2", value=data.get("SN_Ant2",""))
    with c2:
        data["IP_2"] = st.text_input("IP_2", value=data.get("IP_2",""))
        data["SN_SBG2"] = st.text_input("SN_SBG2", value=data.get("SN_SBG2",""))
        data["SN_Septentrio2"] = st.text_input("SN_Septentrio2", value=data.get("SN_Septentrio2",""))
        data["SN_Ant3"] = st.text_input("SN_Ant3", value=data.get("SN_Ant3",""))
        data["SN_Ant4"] = st.text_input("SN_Ant4", value=data.get("SN_Ant4",""))

    st.subheader("Document References")
    c3, c4 = st.columns(2)
    with c3:
        data["MCRDocumentReference"] = st.text_input("MCRDocumentReference", value=data.get("MCRDocumentReference",""))
        data["DocumentReference8"] = st.text_input("DocumentReference8", value=data.get("DocumentReference8",""))
    with c4:
        data["DIMCONDocumentReference"] = st.text_input("DIMCONDocumentReference", value=data.get("DIMCONDocumentReference",""))
        data["DocumentReference9"] = st.text_input("DocumentReference9", value=data.get("DocumentReference9",""))

    if st.form_submit_button("Save changes"):
        st.success("Saved.")
# -----------------------------------------------------

# ---------------- Render & Download (always render) ----------------
if st.button("Render reports"):
    try:
        if imports_ok.get("core.models") is not True or imports_ok.get("core.renderer") is not True:
            raise RuntimeError("Core modules failed to import; see Debug panel below.")
        from core.models import JobData  # re-import after possible reloads

        # validate your static fields and merge Excel values
        job = JobData.model_validate(data)
        combined = {**job.model_dump(), **st.session_state.get("excel_vals", {})}
        outputs = render_all_to_memory(combined, SPECS_DIR)
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
# ------------------------------------------------------------------

# ---------------- Debug panel (so you can see what's failing) ----------------
with st.expander("Debug (advanced)"):
    st.write("Repo root:", str(ROOT))
    st.write("Specs dir exists:", (SPECS_DIR.exists(), str(SPECS_DIR)))
    st.write("Imports:", {k: (True if v is True else f"{type(v).__name__}: {v}") for k, v in imports_ok.items()})
    st.write("Excel bytes present:", excel_bytes is not None)
    st.write("Excel values count:", len(st.session_state.get("excel_vals", {})))
