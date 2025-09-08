# --- add this at the very top of app/streamlit_app.py ---
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]   # the repo root (…/reportgen)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --------------------------------------------------------
# app/streamlit_app.py
import streamlit as st
from pathlib import Path
from io import BytesIO
import zipfile, json
import yaml
from pydantic import ValidationError
from jinja2.exceptions import UndefinedError

from core.models import JobData
from core.renderer import render_all_to_memory
from core.linter import lint

SPECS_DIR = Path("template_specs")

st.set_page_config(page_title="ReportGen", layout="wide")

# session state
if "jobs" not in st.session_state:
    st.session_state.jobs = {"Job 1": {"ProjectName":"", "Date":"2025-01-01"}}
if "current_job" not in st.session_state:
    st.session_state.current_job = "Job 1"
if "rendered" not in st.session_state:
    st.session_state.rendered = {}

# --- Sidebar ---
with st.sidebar:
    st.title("ReportGen")

    # choose job
    names = list(st.session_state.jobs.keys())
    pick = st.selectbox("Choose job", names, index=names.index(st.session_state.current_job))
    if pick != st.session_state.current_job:
        st.session_state.current_job = pick

    # new / copy
    c1, c2 = st.columns(2)
    if c1.button("New job"):
        name = f"Job {len(st.session_state.jobs)+1}"
        st.session_state.jobs[name] = {}
        st.session_state.current_job = name
    if c2.button("Copy job"):
        name = f"{st.session_state.current_job} (copy)"
        st.session_state.jobs[name] = dict(st.session_state.jobs[st.session_state.current_job])
        st.session_state.current_job = name

    st.divider()

    # load file
    up = st.file_uploader("Load YAML/JSON", type=["yaml","yml","json"])
    if up:
        try:
            data = yaml.safe_load(up.read()) if up.name.endswith((".yaml",".yml")) else json.loads(up.read())
            st.session_state.jobs[st.session_state.current_job] = data or {}
            st.success("Loaded.")
        except Exception as e:
            st.error(f"Could not load: {e}")

    # save file
    cur = st.session_state.jobs[st.session_state.current_job]
    st.download_button("Save as YAML", yaml.safe_dump(cur or {}, sort_keys=False, allow_unicode=True), file_name=f"{st.session_state.current_job}.yaml")
    st.download_button("Save as JSON", json.dumps(cur or {}, indent=2, ensure_ascii=False), file_name=f"{st.session_state.current_job}.json")

    st.divider()
    if st.button("Placeholder linter"):
        rep = lint(SPECS_DIR, cur or {})
        for r in rep:
            if r["unresolved"]:
                st.error(f"{r['template']}: {', '.join(r['unresolved'])}")
            else:
                st.success(f"{r['template']}: all good")

# --- Main: form ---
st.header(f"Edit: {st.session_state.current_job}")
data = st.session_state.jobs[st.session_state.current_job]

with st.form("job-form"):
    # simple fields (add more as you need)
    data["ProjectName"] = st.text_input("ProjectName", value=data.get("ProjectName",""))
    data["ClientName"]  = st.text_input("ClientName",  value=data.get("ClientName",""))
    data["Date"]        = st.text_input("Date (YYYY-MM-DD)", value=str(data.get("Date","2025-01-01")))
    data["SurveyVessel"]= st.text_input("SurveyVessel", value=data.get("SurveyVessel",""))
    data["Notes"]       = st.text_area("Notes", value=data.get("Notes",""))

    submitted = st.form_submit_button("Save changes")
    if submitted:
        st.session_state.jobs[st.session_state.current_job] = data
        st.success("Saved.")

st.subheader("Make reports")
if st.button("Render all"):
    try:
        # Pydantic check
        job = JobData.model_validate(data)
        outputs = render_all_to_memory(job.model_dump(), SPECS_DIR)
        st.session_state.rendered = outputs
        st.success(f"Made {len(outputs)} file(s). See buttons below.")
    except ValidationError as ve:
        st.error("Your data has a problem.")
        st.caption("Example: missing ProjectName, or Date not like 2025-01-31.")
        with st.expander("Details"):
            for e in ve.errors():
                st.write(f"{e['loc']}: {e['msg']}")
    except UndefinedError as ue:
        st.error("A placeholder in the template was not found.")
        st.caption("Open the linter in the sidebar to see which one.")
    except ValueError as ve:
        st.error(str(ve))
    except Exception as e:
        st.error(f"Something else went wrong: {e}")

# download buttons
if st.session_state.rendered:
    st.success("Downloads:")
    for fname, blob in st.session_state.rendered.items():
        name = Path(fname).name
        st.download_button(f"Download {name}", data=blob, file_name=name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # ZIP
    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, blob in st.session_state.rendered.items():
            zf.writestr(Path(fname).name, blob)
    st.download_button("Download ALL as ZIP", data=zbuf.getvalue(), file_name="reports.zip", mime="application/zip")
