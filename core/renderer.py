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

def render_all_to_memory(job_dict: dict, specs_dir: Path) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}

    for spec in load_spec_files(specs_dir):
        template_path = Path(spec.template_file)

        # 1) Hard guard: file exists and is a DOCX (zip starts with PK)
        if not template_path.is_file():
            raise FileNotFoundError(f"[{spec.name}] Template not found: {template_path}")
        magic = template_path.read_bytes()[:4]
        if magic != b"PK\x03\x04":
            raise ValueError(f"[{spec.name}] Not a valid .docx (zip) file: {template_path}")

        # 2) Build context + required fields check
        context = build_context(job_dict, spec.aliases)
        missing = get_required_missing(context, spec.required_fields)
        if missing:
            raise ValueError(f"[{spec.name}] Missing required fields: {', '.join(missing)}")

        # 3) Load template and register filters
        tpl = DocxTemplate(str(template_path))
        if tpl is None or not hasattr(tpl, "jinja_env"):
            raise RuntimeError(f"[{spec.name}] Failed to load template object: {template_path}")

        tpl.jinja_env.undefined = StrictUndefined
        tpl.jinja_env.filters["datetimeformat"] = datetimeformat

        # 4) Render
        tpl.render(context)

        # 5) Output name and bytes (DO NOT assign tpl = tpl.save(...))
        out_name = _eval_output_pattern(spec.output_pattern, context)
        buf = BytesIO()
        tpl.save(buf)               # returns None — that's OK
        outputs[out_name] = buf.getvalue()

    return outputs
