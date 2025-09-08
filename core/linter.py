# core/linter.py
from pathlib import Path
from docxtpl import DocxTemplate
from .specs import load_spec_files
from .renderer import build_context

def _flatten_keys(d, parent=""):
    keys = set()
    for k, v in (d or {}).items():
        full = f"{parent}.{k}" if parent else k
        keys.add(full)
        if isinstance(v, dict):
            keys |= _flatten_keys(v, full)
    return keys

def lint(specs_dir: Path, job_dict: dict):
    report = []
    for spec in load_spec_files(specs_dir):
        entry = {
            "template": spec.name,
            "template_file": str(spec.template_file),
            "unresolved": [],
            "error": None,
        }
        try:
            if not Path(spec.template_file).is_file():
                entry["error"] = f"Template not found: {spec.template_file}"
                report.append(entry); continue

            tpl = DocxTemplate(str(spec.template_file))
            declared = set(tpl.get_undeclared_template_variables())
            ctx = build_context(job_dict, spec.aliases)
            available = _flatten_keys(ctx)
            unresolved = [v for v in declared
                          if v not in available and not any(v.startswith(a + ".") for a in available)]
            entry["unresolved"] = sorted(unresolved)
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"
        report.append(entry)
    return report
