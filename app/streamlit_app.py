from pathlib import Path
from io import BytesIO
import streamlit as st
from pydantic import ValidationError
from jinja2.exceptions import UndefinedError
import zipfile
# --- make repo root importable ---
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]  # .../reportgen
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ---------------------------------
from core.models import JobData
from core.renderer import render_all_to_memory

# repo root + specs dir
ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "template_specs"

st.set_page_config(page_title="Caisson Reports", layout="centered")
st.title("Caisson Reports")

from core.excel_parser import list_sheet_names, parse_excel_nodes

st.subheader("Excel nodes (optional)")
uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

# keep parsed excel values in session
excel_vals = st.session_state.setdefault("excel_vals", {})

if uploaded:
    try:
        # list sheets for user to choose
        sheets = list_sheet_names(uploaded)
        sheet = st.selectbox("Choose sheet", sheets, key="sheet_pick")

        # let user specify column names if their sheet uses different headers
        with st.expander("Columns (change if headers differ)", expanded=False):
            node_col = st.text_input("Node column", value="Node")
            x_col = st.text_input("X column", value="X")
            y_col = st.text_input("Y column", value="Y")
            z_col = st.text_input("Z column", value="Z")

        # (optional) filter which nodes to include
        filter_text = st.text_input("Only include these node names (comma separated)", value="")
        only_nodes = [s.strip() for s in filter_text.split(",") if s.strip()] or None

        if st.button("Load nodes from Excel"):
            # IMPORTANT: uploaded is a stream; re-seek to start before each read
            uploaded.seek(0)
            excel_vals = parse_excel_nodes(
                uploaded, sheet_name=sheet,
                node_col=node_col, x_col=x_col, y_col=y_col, z_col=z_col,
                only_nodes=only_nodes
            )
            st.session_state["excel_vals"] = excel_vals
            st.success(f"Loaded {len(excel_vals)} placeholders from sheet '{sheet}'.")
            # small preview
            preview_keys = sorted(list(excel_vals.keys()))[:12]
            if preview_keys:
                st.caption("Preview (first ~12 keys):")
                st.code(", ".join(preview_keys))
    except Exception as e:
        st.error(f"Excel error: {e}")


# keep one data dict in session
if "data" not in st.session_state:
    st.session_state.data = {}

data = st.session_state.data

# defaults so inputs always show
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

    submitted = st.form_submit_button("Save changes")
    if submitted:
        st.success("Saved.")

# Render
if st.button("Render reports"):
    try:
        # validate your static fields only
        job = JobData.model_validate(data)
        # combine with excel-derived placeholders
        combined = {**job.model_dump(), **st.session_state.get("excel_vals", {})}
        outputs = render_all_to_memory(combined, SPECS_DIR)
        st.session_state["rendered"] = outputs
        st.success(f"Generated {len(outputs)} report(s).")
    except ValidationError as ve:
        st.error("Some required data is missing or invalid.")
        with st.expander("Details"):
            for e in ve.errors():
                st.write(f"{e['loc']}: {e['msg']}")
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        import traceback; st.code("".join(traceback.format_exc()))

# Download
if "rendered" in st.session_state and st.session_state.rendered:
    st.subheader("Download")
    for fname, blob in st.session_state.rendered.items():
        name = Path(fname).name
        st.download_button(f"Download {name}", data=blob, file_name=name)

    if len(st.session_state.rendered) > 1:
        zbuf = BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, blob in st.session_state.rendered.items():
                zf.writestr(Path(fname).name, blob)
        st.download_button("Download ALL as ZIP", data=zbuf.getvalue(), file_name="reports.zip", mime="application/zip")
