# core/specs.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping
import yaml

ROOT = Path(__file__).resolve().parents[1]  # .../reportgen

@dataclass
class TemplateSpec:
    name: str
    template_file: Path
    output_pattern: str
    required_fields: List[str]
    aliases: Dict[str, str]

def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def load_spec_files(specs_dir: Path) -> List[TemplateSpec]:
    specs: List[TemplateSpec] = []
    for p in specs_dir.glob("*.yaml"):
        s = load_yaml(p)
        tpl_path = (ROOT / s["template_file"]).resolve()
        specs.append(TemplateSpec(
            name=p.stem,
            template_file=tpl_path,
            output_pattern=s["output_pattern"],
            required_fields=s.get("required_fields", []),
            aliases=s.get("aliases", {}),
        ))
    return specs

def _get_by_dotted(d: Mapping[str, Any], dotted: str):
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur

def _set_by_dotted(d: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value

def build_context(job_dict: Dict[str, Any], aliases: Dict[str, str]) -> Dict[str, Any]:
    """Apply aliases into a copy of the job dict (supports dotted paths)."""
    context = dict(job_dict)
    for alias_name, dotted in (aliases or {}).items():
        # allow alias with "__" to mean a dot in the alias name
        _set_by_dotted(context, alias_name.replace("__", "."), _get_by_dotted(job_dict, dotted))
    return context

def get_required_missing(context: Mapping[str, Any], required_fields: List[str]) -> List[str]:
    missing: List[str] = []
    for rf in required_fields:
        cur: Any = context
        ok = True
        for part in rf.split("."):
            if not isinstance(cur, Mapping) or part not in cur:
                ok = False
                break
            cur = cur[part]
        if not ok or cur in (None, ""):
            missing.append(rf)
    return missing
