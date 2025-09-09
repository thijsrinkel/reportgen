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

st.set_page_config(page_title="MOG 2 MCR & DIMCON Report Generator", layout="centered")
st.title("MOG 2 MCR & DIMCON Report Generator")

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
    # NOTE: this should be the openpyxl-only parser if you removed pandas
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

excel_vals = st.session_state.setdefault("excel_vals", {})
excel_bytes = st.session_state.get("excel_bytes")

if uploaded:
    excel_bytes = uploaded.getvalue()  # single read
    st.session_state["excel_bytes"] = excel_bytes

if excel_bytes and excel_ready:
    try:
        # list sheets
        sheets = list_sheet_names_bytes(excel_bytes)
        sheet = st.selectbox("Choose sheet", sheets, key="sheet_pick")

        # header handling + column specs
        with st.expander("Columns / header options", expanded=False):
            has_header = st.checkbox("My sheet has a header row", value=True)
            if has_header:
                node_col = st.text_input("Node column (header name or letter)", value="D")
                x_col    = st.text_input("X column (header name or letter)", value="H")
                y_col    = st.text_input("Y column (header name or letter)", value="I")
                z_col    = st.text_input("Z column (header name or letter)", value="J")
            else:
                node_col = st.text_input("Node column (letter or 1-based index)", value="D")
                x_col    = st.text_input("X column (letter or 1-based index)", value="H")
                y_col    = st.text_input("Y column (letter or 1-based index)", value="I")
                z_col    = st.text_input("Z column (letter or 1-based index)", value="J")

        filter_text = st.text_input("Only include these node names (comma separated)", value="")
        only_nodes = [s.strip() for s in filter_text.split(",") if s.strip()] or None

        # >>> this button & viewer MUST be inside the try: block <<<
        if st.button("Load nodes from Excel"):
            excel_vals = parse_excel_nodes_bytes(
                excel_bytes,
                sheet_name=sheet,
                node_col=node_col, x_col=x_col, y_col=y_col, z_col=z_col,
                only_nodes=only_nodes,
                has_header=has_header,
            )
            st.session_state["excel_vals"] = excel_vals
            st.success(f"Loaded {len(excel_vals)} placeholders from '{sheet}'.")

            # ---- FULL VIEWER (all placeholders) ----
            all_items = sorted(excel_vals.items(), key=lambda kv: kv[0])
            st.caption(f"{len(all_items)} placeholders loaded.")

            q = st.text_input("Filter placeholders (case-insensitive)", value="")
            if q:
                ql = q.lower()
                view_items = [kv for kv in all_items if ql in kv[0].lower()]
            else:
                view_items = all_items

            # optional paging for very large lists
            PAGE_SIZE = 200
            num_pages = max(1, (len(view_items) + PAGE_SIZE - 1) // PAGE_SIZE)
            page = st.number_input("Page", min_value=1, max_value=num_pages, value=1, step=1)
            start = (page - 1) * PAGE_SIZE
            end = start + PAGE_SIZE
            page_items = view_items[start:end]

            rows = [{"placeholder": k, "value": v} for k, v in page_items]
            st.dataframe(rows, hide_index=True, use_container_width=True)

            with st.expander("Show ALL placeholder names as text"):
                st.text_area("Names", "\n".join(k for k, _ in view_items), height=300)

            import json, yaml
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
            # -----------------------------------------

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
    "Roll_IP1": "", "Pitch_IP1": "", "Yaw_IP1": "",
    "Roll_IP2": "", "Pitch_IP2": "", "Yaw_IP2": "",
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
        data["Roll_IP1"] = st.text_input("Roll_IP1", value=data.get("Roll_IP1",""))
        data["Pitch_IP1"] = st.text_input("Pitch_IP1", value=data.get("Pitch_IP1",""))
        data["Yaw_IP1"] = st.text_input("Yaw_IP1", value=data.get("Yaw_IP1",""))
    with c2:
        data["IP_2"] = st.text_input("IP_2", value=data.get("IP_2",""))
        data["SN_SBG2"] = st.text_input("SN_SBG2", value=data.get("SN_SBG2",""))
        data["SN_Septentrio2"] = st.text_input("SN_Septentrio2", value=data.get("SN_Septentrio2",""))
        data["SN_Ant3"] = st.text_input("SN_Ant3", value=data.get("SN_Ant3",""))
        data["SN_Ant4"] = st.text_input("SN_Ant4", value=data.get("SN_Ant4",""))
        data["Roll_IP2"] = st.text_input("Roll_IP2", value=data.get("Roll_IP2",""))
        data["Pitch_IP2"] = st.text_input("Pitch_IP2", value=data.get("Pitch_IP2",""))
        data["Yaw_IP2"] = st.text_input("Yaw_IP2", value=data.get("Yaw_IP2",""))

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
    st.write("Excel bytes present:", st.session_state.get("excel_bytes") is not None)
    st.write("Excel values count:", len(st.session_state.get("excel_vals", {})))
