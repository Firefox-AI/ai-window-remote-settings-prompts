#!/usr/bin/env python3
"""
Assemble v2 prompts the same way Firefox's PromptLoader.sys.mjs would, and
dump the result to JSON. Lets you eyeball or diff the final system prompt
each model receives without spinning up Firefox.

Mirrors:
- moz-src:///browser/components/aiwindow/models/PromptLoader.sys.mjs
  -> buildChatSystemPrompt(model)
- The same module order, model->generic fallback, and {skill_list} +
  template-value substitution.

Usage:
    python3 tools/assemble_v2_prompts.py [--out PATH] [--model MODEL ...]
        [--show-prompt]

Default writes build/v2_prompts.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
V2_ROOT = REPO_ROOT / "prompts_v2"

# Mirrors CHAT_SYSTEM_PROMPT_MODULES in PromptLoader.sys.mjs.
CHAT_MODULES = [
    "identity",
    "model-details",
    "style",
    "skills",
    "trust-and-safety",
    "response-rules",
    "browser-context",
]
BROWSER_CONTEXT_FRAGMENTS = ["date", "tab", "mentions"]
GENERIC_MODEL = "generic"
SEPARATOR = "\n\n\n"
FRAGMENT_SEPARATOR = "\n\n"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_models() -> set[str]:
    """Union of every model identifier that appears anywhere under prompts_v2."""
    models: set[str] = set()
    for f in V2_ROOT.rglob("*.md"):
        models.add(f.stem)
    for f in V2_ROOT.rglob("*.json"):
        models.add(f.stem)
    models.discard("")
    return models


def load_chat_module(module: str, model: str) -> tuple[str | None, str | None]:
    """Return (prompts_text, resolved_model) for the chat module/model, with
    model->generic fallback. Returns (None, None) if neither exists."""
    base = V2_ROOT / "features" / "chat" / module / "v1"
    for candidate in (model, GENERIC_MODEL):
        md = base / f"{candidate}.md"
        if md.exists():
            return _read_text(md).rstrip(), candidate
    return None, None


def load_browser_context_fragment(fragment: str, model: str) -> str | None:
    base = V2_ROOT / "features" / "browser-context" / fragment / "v1"
    for candidate in (model, GENERIC_MODEL):
        md = base / f"{candidate}.md"
        if md.exists():
            return _read_text(md).rstrip()
    return None


def list_skills(model: str) -> list[dict]:
    """All skill records as {name, description, prompts, model}, sorted by
    name; model-specific entries override the generic for the same name."""
    skills_root = V2_ROOT / "skills"
    if not skills_root.exists():
        return []
    by_name: dict[str, dict] = {}
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        v1 = skill_dir / "v1"
        if not v1.exists():
            continue
        for candidate in (GENERIC_MODEL, model):
            md = v1 / f"{candidate}.md"
            meta = v1 / f"{candidate}.json"
            if md.exists():
                description = ""
                if meta.exists():
                    description = _read_json(meta).get("description", "")
                by_name[skill_dir.name] = {
                    "name": skill_dir.name,
                    "description": description,
                    "prompts": _read_text(md).rstrip(),
                    "model": candidate,
                }
    return sorted(by_name.values(), key=lambda s: s["name"])


def format_skill_list(skills: list[dict]) -> str:
    return "\n".join(
        f"- <name>{s['name']}</name><description>{s['description']}</description>"
        for s in skills
    )


def render_template(text: str, substitutions: dict[str, str]) -> str:
    for name, value in substitutions.items():
        text = text.replace(f"{{{name}}}", value if value is not None else "")
    return text


def build_chat_system_prompt(
    model: str,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now()
    iso_ts = now.strftime("%Y-%m-%dT%H:%M:%S")
    today_date = iso_ts.split("T")[0]

    sections = []
    used_modules: list[dict] = []
    missing_modules: list[str] = []
    for module in CHAT_MODULES:
        text, resolved = load_chat_module(module, model)
        if not text:
            missing_modules.append(module)
            continue
        sections.append(text)
        used_modules.append({"module": module, "resolved_model": resolved})

    skills = list_skills(model)
    skill_list = format_skill_list(skills)

    substitutions = {
        "skill_list": skill_list,
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "isoTimestamp": iso_ts,
        "todayDate": today_date,
    }
    body = SEPARATOR.join(sections)
    body = render_template(body, substitutions)

    return {
        "model": model,
        "system_prompt": body,
        "modules_resolved": used_modules,
        "modules_missing": missing_modules,
        "skills": [
            {"name": s["name"], "model": s["model"], "description": s["description"]}
            for s in skills
        ],
        "substitutions_applied": list(substitutions.keys()),
        "char_count": len(body),
    }


def build_browser_context_prompt(model: str) -> dict:
    fragments_present: list[dict] = []
    fragments_missing: list[str] = []
    for fragment in BROWSER_CONTEXT_FRAGMENTS:
        text = load_browser_context_fragment(fragment, model)
        if text is None:
            fragments_missing.append(fragment)
        else:
            fragments_present.append({"fragment": fragment, "prompts": text})
    return {
        "model": model,
        "fragments_present": [f["fragment"] for f in fragments_present],
        "fragments_missing": fragments_missing,
        "fragments": fragments_present,
    }


def load_chat_params(model: str) -> dict | None:
    base = V2_ROOT / "features" / "chat" / "params" / "v1"
    for candidate in (model, GENERIC_MODEL):
        f = base / f"{candidate}.json"
        if f.exists():
            data = _read_json(f)
            data["_resolved_model"] = candidate
            return data
    return None


def assemble(
    models: list[str] | None,
    now: datetime | None = None,
) -> dict:
    discovered = discover_models()
    targets = sorted(models or discovered)
    out = {
        "generated_at": (now or datetime.now()).isoformat(timespec="seconds"),
        "discovered_models": sorted(discovered),
        "module_order": list(CHAT_MODULES),
        "models": {},
    }
    for model in targets:
        out["models"][model] = {
            "chat": build_chat_system_prompt(model, now=now),
            "browser_context": build_browser_context_prompt(model),
            "params": load_chat_params(model),
        }
    return out


def _detect_unresolved_placeholders(text: str) -> list[str]:
    return sorted(set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", text)))


def build_records_dump() -> list[dict]:
    """Emit the RS records array shape that Patch B's loadV2Records consumes.

    Walks prompts_v2/ once and produces one record per .md (modules + skills
    + browser-context fragments). Matching Patch B's record filter:
        r.kind in {"module", "skill"} and r.id contains `--v1--`.
    """
    records: list[dict] = []
    chat_root = V2_ROOT / "features" / "chat"
    if chat_root.exists():
        for module_dir in sorted(chat_root.iterdir()):
            if not module_dir.is_dir() or module_dir.name == "params":
                continue
            v1 = module_dir / "v1"
            if not v1.exists():
                continue
            for md in sorted(v1.glob("*.md")):
                records.append({
                    "id": f"chat--{module_dir.name}--v1--{md.stem}",
                    "kind": "module",
                    "feature": "chat",
                    "module": module_dir.name,
                    "model": md.stem,
                    "prompts": _read_text(md),
                })

    bc_root = V2_ROOT / "features" / "browser-context"
    if bc_root.exists():
        for fragment_dir in sorted(bc_root.iterdir()):
            if not fragment_dir.is_dir():
                continue
            v1 = fragment_dir / "v1"
            if not v1.exists():
                continue
            for md in sorted(v1.glob("*.md")):
                records.append({
                    "id": f"browser-context--{fragment_dir.name}--v1--{md.stem}",
                    "kind": "module",
                    "feature": "browser-context",
                    "module": fragment_dir.name,
                    "model": md.stem,
                    "prompts": _read_text(md),
                })

    skills_root = V2_ROOT / "skills"
    if skills_root.exists():
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            v1 = skill_dir / "v1"
            if not v1.exists():
                continue
            for md in sorted(v1.glob("*.md")):
                meta_path = v1 / f"{md.stem}.json"
                description = ""
                if meta_path.exists():
                    description = _read_json(meta_path).get("description", "")
                records.append({
                    "id": f"skill--{skill_dir.name}--v1--{md.stem}",
                    "kind": "skill",
                    "name": skill_dir.name,
                    "model": md.stem,
                    "description": description,
                    "prompts": _read_text(md),
                })

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "build" / "v2_prompts.json"),
        help="Output JSON path (default: build/v2_prompts.json).",
    )
    parser.add_argument(
        "--model",
        action="append",
        help="Only assemble for this model (repeatable). Default: all discovered.",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Also print the assembled system prompt for each model to stdout.",
    )
    parser.add_argument(
        "--records-out",
        default=str(REPO_ROOT / "build" / "v2_records.json"),
        help="Output path for the RS records array dump (default: build/v2_records.json).",
    )
    args = parser.parse_args()

    bundle = assemble(args.model)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    records = build_records_dump()
    records_path = Path(args.records_out)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path.relative_to(REPO_ROOT)}")
    print(f"  models: {', '.join(sorted(bundle['models']))}")
    print(f"Wrote {records_path.relative_to(REPO_ROOT)}")
    record_kinds: dict[str, int] = {}
    for r in records:
        record_kinds[r["kind"]] = record_kinds.get(r["kind"], 0) + 1
    print(f"  records: {len(records)} total ({', '.join(f'{k}={v}' for k, v in sorted(record_kinds.items()))})")

    any_unresolved = False
    for model, payload in bundle["models"].items():
        chat = payload["chat"]
        unresolved = _detect_unresolved_placeholders(chat["system_prompt"])
        if unresolved:
            any_unresolved = True
            print(f"  WARN {model}: unresolved placeholders in chat prompt: {unresolved}")
        if chat["modules_missing"]:
            print(f"  INFO {model}: missing chat modules (will use generic fallback): {chat['modules_missing']}")
        if payload["browser_context"]["fragments_missing"]:
            print(f"  INFO {model}: missing browser-context fragments: {payload['browser_context']['fragments_missing']}")
        if payload["params"] is None:
            print(f"  INFO {model}: no params file")

        if args.show_prompt:
            print()
            print(f"===== {model} =====")
            print(chat["system_prompt"])

    return 1 if any_unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
