# core/specs.py
from dataclasses import dataclass
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]  # .../reportgen

@dataclass
class TemplateSpec:
    name: str
    template_file: Path
    output_pattern: str
    required_fields: list
    aliases: dict

def load_spec_files(specs_dir: Path):
    specs = []
    for p in specs_dir.glob("*.yaml"):
        s = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        tpl_path = (ROOT / s["template_file"]).resolve()  # << key line
        specs.append(TemplateSpec(
            name=p.stem,
            template_file=tpl_path,
            output_pattern=s["output_pattern"],
            required_fields=s.get("required_fields", []),
            aliases=s.get("aliases", {}),
        ))
    return specs
