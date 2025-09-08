from pathlib import Path
from io import BytesIO
import streamlit as st
from pydantic import ValidationError
from jinja2.exceptions import UndefinedError
import zipfile

from core.models import JobData
from core.renderer import render_all_to_memory

# repo root + specs dir
ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "template_specs"

st.set_page_config(page_title="Caisson Reports", layout="centered")
st.title("Caisson Reports")

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
        job = JobData.model_validate(data)                      # schema check
        outputs = render_all_to_memory(job.model_dump(), SPECS_DIR)  # both templates
        st.session_state.rendered = outputs
        st.success(f"Generated {len(outputs)} report(s).")
    except ValidationError as ve:
        st.error("Some required data is missing or invalid.")
        with st.expander("Details"):
            for e in ve.errors():
                st.write(f"{e['loc']}: {e['msg']}")
    except UndefinedError as ue:
        st.error("Template contains a placeholder your data doesn't have.")
        with st.expander("Details"):
            st.write(str(ue))
    except Exception as e:
        st.error(f"Something went wrong: {e}")

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
