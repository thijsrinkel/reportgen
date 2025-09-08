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

SPECS_DIR = ROOT / "template_specs"

st.set_page_config(page_title="ReportGen", layout="wide")

tmpl_dir = ROOT / "templates"
st.caption(f"Templates dir: {tmpl_dir}")
st.caption(f"Templates found: {[p.name for p in tmpl_dir.glob('*.docx')]}")

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
    json_text = json.dumps(cur or {}, indent=2, ensure_ascii=False, default=str)
    st.download_button("Save as JSON", json_text, file_name=f"{st.session_state.current_job}.json")


    st.divider()
    if st.button("Placeholder linter"):
        rep = lint(SPECS_DIR, cur or {})
        for r in rep:
            st.subheader(f"Template: {r['template']}")
            st.caption(f"Path: {r['template_file']}")
            if r.get("error"):
                st.error(r["error"])
            elif r["unresolved"]:
                st.error("Unresolved: " + ", ".join(r["unresolved"]))
            else:
                st.success("All placeholders look resolvable.")


# --- Main: form ---
st.header(f"Edit: {st.session_state.current_job}")
data = st.session_state.jobs[st.session_state.current_job]

# defaults so fields always show
defaults = {
    "CaissonNumber": "",
    "IP_1": "", "IP_2": "",
    "SN_SBG1": "", "SN_Septentrio1": "", "SN_Ant1": "", "SN_Ant2": "",
    "SN_SBG2": "", "SN_Septentrio2": "", "SN_Ant3": "", "SN_Ant4": "",
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

    submitted = st.form_submit_button("Save changes")
    if submitted:
        st.session_state.jobs[st.session_state.current_job] = data
        st.success("Saved.")

st.subheader("Make reports")
if st.button("Render all"):
    try:
        # sanitize before validate
        def _none_if_empty(v):
            if isinstance(v, str) and not v.strip():
                return None
            if isinstance(v, dict) and not any(v.values()):
                return None
            return v
        for key in ("Equipment", "Operators"):
            if key in data:
                data[key] = _none_if_empty(data[key])

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


if st.button("Self-test one template (temporary)"):
    try:
        from docxtpl import DocxTemplate
        from jinja2 import Environment, StrictUndefined
        test_path = (ROOT / "templates" / "cable_report.docx")
        st.write(f"Opening: {test_path}")
        tpl = DocxTemplate(str(test_path))
        env = Environment(undefined=StrictUndefined, autoescape=False)
        env.filters["datetimeformat"] = lambda v, fmt="%Y-%m-%d": str(v)
        tpl.render({"ProjectName": "X", "Date": "2025-01-01"}, jinja_env=env)
        buf = BytesIO(); tpl.save(buf)
        st.success("Self-test passed (opened, rendered, saved).")
    except Exception as e:
        import traceback
        st.error(f"Self-test failed: {e}")
        st.code("".join(traceback.format_exc()))


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
