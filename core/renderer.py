# core/renderer.py
from io import BytesIO
from pathlib import Path
from jinja2 import StrictUndefined, Environment
from docxtpl import DocxTemplate
from .filters import datetimeformat
from .specs import load_spec_files

def _set_by_dotted(d, dotted, val):
    cur = d
    parts = dotted.split(".")
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = val

def _get_by_dotted(d, dotted):
    cur = d
    for p in dotted.split("."):
        if not isinstance(cur, dict): return None
        cur = cur.get(p)
    return cur

def build_context(job_dict, aliases):
    ctx = dict(job_dict)
    for alias, dotted in (aliases or {}).items():
        _set_by_dotted(ctx, alias.replace("__","."), _get_by_dotted(job_dict, dotted))
    return ctx

def render_all_to_memory(job_dict: dict, specs_dir: Path) -> dict[str, bytes]:
    env = Environment(undefined=StrictUndefined)
    env.filters["datetimeformat"] = datetimeformat

    outputs = {}
    for spec in load_spec_files(specs_dir):
        ctx = build_context(job_dict, spec.aliases)

        # check required fields
        missing = []
        for rf in spec.required_fields:
            if not _get_by_dotted(ctx, rf):
                missing.append(rf)
        if missing:
            raise ValueError(f"[{spec.name}] Missing: {', '.join(missing)}")

        tpl = DocxTemplate(str(spec.template_file))
        tpl.jinja_env.undefined = StrictUndefined
        tpl.jinja_env.filters["datetimeformat"] = datetimeformat
        tpl.render(ctx)

        out_name = env.from_string(spec.output_pattern).render(ctx)
        buf = BytesIO()
        tpl.save(buf)
        outputs[out_name] = buf.getvalue()
    return outputs
