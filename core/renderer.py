# core/renderer.py
from io import BytesIO
from pathlib import Path
from jinja2 import StrictUndefined, Environment
from docxtpl import DocxTemplate
from typing import Dict, Any

from .filters import datetimeformat
from .specs import load_spec_files, build_context, get_required_missing

def _eval_output_pattern(pattern: str, context: dict) -> str:
    env = Environment(undefined=StrictUndefined)
    env.filters["datetimeformat"] = datetimeformat
    return env.from_string(pattern).render(context)

def render_all_to_memory(job_dict: Dict[str, Any], specs_dir: Path) -> Dict[str, bytes]:
    outputs: Dict[str, bytes] = {}
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

        tpl = DocxTemplate(str(template_path))
        tpl.jinja_env.undefined = StrictUndefined
        tpl.jinja_env.filters["datetimeformat"] = datetimeformat
        tpl.render(context)

        out_name = _eval_output_pattern(spec.output_pattern, context)
        buf = BytesIO()
        tpl.save(buf)  # returns None; buf holds the bytes
        outputs[out_name] = buf.getvalue()
    return outputs
