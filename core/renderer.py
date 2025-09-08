# core/renderer.py
from io import BytesIO
from pathlib import Path
from typing import Dict, Any
from jinja2 import StrictUndefined, Environment
from docxtpl import DocxTemplate
from .filters import datetimeformat
from .specs import load_spec_files, build_context, get_required_missing

def _make_env() -> Environment:
    env = Environment(undefined=StrictUndefined, autoescape=False)
    env.filters["datetimeformat"] = datetimeformat
    return env

def _eval_output_pattern(pattern: str, context: dict) -> str:
    env = _make_env()
    return env.from_string(pattern).render(context)

def render_all_to_memory(job_dict: Dict[str, Any], specs_dir: Path) -> Dict[str, bytes]:
    outputs: Dict[str, bytes] = {}
    env = _make_env()

    for spec in load_spec_files(specs_dir):
        template_path = Path(spec.template_file)
        if not template_path.is_file():
            raise FileNotFoundError(f"[{spec.name}] Template not found: {template_path}")
        if template_path.read_bytes()[:4] != b"PK\x03\x04":
            raise ValueError(f"[{spec.name}] Not a valid .docx (zip) file: {template_path}")

        context = build_context(job_dict, spec.aliases)
        missing = get_required_missing(context, spec.required_fields)
        if missing:
            raise ValueError(f"[{spec.name}] Missing required fields: {', '.join(missing)}")

        tpl = DocxTemplate(str(template_path))  # don't touch tpl.jinja_env
        tpl.render(context, jinja_env=env)      # supply our env here

        out_name = _eval_output_pattern(spec.output_pattern, context)
        buf = BytesIO()
        tpl.save(buf)
        outputs[out_name] = buf.getvalue()

    return outputs
