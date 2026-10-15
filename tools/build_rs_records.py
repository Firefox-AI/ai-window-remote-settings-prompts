#!/usr/bin/env python3
"""
Compile this repo (any branch) into the Remote Settings records Firefox reads
for the "ai-window-prompts" collection, so a local Firefox can be pointed at a
branch's prompts without rebuilding anything.

Usage:
    # current checkout -> build/prompt-records.json + build/import-prompts.js
    python3 tools/build_rs_records.py

    # some other branch, without switching your working tree
    python3 tools/build_rs_records.py --ref origin/my-branch

    # only the records you care about (smaller, easier to eyeball)
    python3 tools/build_rs_records.py --feature aitab

Then follow the printed instructions: set two prefs in about:config and paste
the generated snippet into the Browser Console. See docs/testing-in-firefox.md.

The record-building logic mirrors the hourly updater that publishes to Remote
Settings (mozilla/remote-settings-ai-window-prompts-updater). When that package
is installed its collectors are used directly; otherwise the local copy below
(same logic, kept in sync the way test_v2.py is) runs instead.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION = "ai-window-prompts"


# ---------------------------------------------------------------------------
# Record collection (mirrors the updater's collect_prompts_and_params /
# collect_v2_records; see module docstring).


def get_item(major_version_dir, model_name):
    with open(major_version_dir / f"{model_name}.json", "r") as f:
        data = json.load(f)
    with open(major_version_dir / f"{model_name}.md", "r") as f:
        prompt = f.read()

    data["prompts"] = prompt
    data["id"] = f"{data['feature']}--{data['model'].replace('.', '-')}--{major_version_dir.stem}"
    data["parameters"] = json.dumps(data["parameters"])
    data["model_details"] = json.dumps(data.get("model_details", {}))

    return data


def collect_prompts_and_params(prompts_dir):
    items = []
    for feature_dir in prompts_dir.iterdir():
        if not feature_dir.is_dir():
            continue
        for major_version_dir in feature_dir.iterdir():
            if not major_version_dir.is_dir():
                continue
            for f in major_version_dir.iterdir():
                if f.suffix == ".md":
                    continue
                items.append(get_item(major_version_dir, f.stem))
    return items


def _normalize_model(stem):
    return stem.replace(".", "-")


def _major_of(version_segment):
    head = str(version_segment).lstrip("vV").split(".")[0]
    return int(head) if head.isdigit() else None


def _module_version(version_segment):
    major = _major_of(version_segment)
    return f"{major}.0" if major is not None else "1.0"


def _read_json_if_exists(path):
    if path is None or not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f) or {}


def _pair_files_by_stem(directory):
    pairs = {}
    for f in directory.iterdir():
        if f.is_file() and f.suffix in (".json", ".md"):
            pairs.setdefault(f.stem, {})[f.suffix] = f
    return pairs


def _collect_manifest_versions(prompts_v2_dir):
    """(feature, module, major) -> version string, from each feature's params
    `modules` manifest. The manifest is the source of truth for module
    versions, so module records are stamped from here."""
    versions = {}
    features_dir = prompts_v2_dir / "features"
    if not features_dir.exists():
        return versions
    for feature_dir in sorted(features_dir.iterdir()):
        params_root = feature_dir / "params"
        if not params_root.is_dir():
            continue
        for version_dir in sorted(params_root.iterdir()):
            if not version_dir.is_dir():
                continue
            for f in sorted(version_dir.glob("*.json")):
                seen = set()
                for entry in _read_json_if_exists(f).get("modules", []):
                    name, version = entry.get("name"), entry.get("version")
                    if not name or version is None:
                        raise ValueError(f"{f}: each `modules` entry needs a 'name' and 'version'")
                    if not isinstance(version, str):
                        raise ValueError(
                            f"{f}: module '{name}' version {version!r} must be a string "
                            '(quote it in JSON, e.g. "1.0" not 1.0)'
                        )
                    if not re.fullmatch(r"v?\d+\.\d+", version):
                        raise ValueError(
                            f"{f}: module '{name}' version '{version}' must be "
                            "'major.minor' (e.g. '1.0')"
                        )
                    if name in seen:
                        raise ValueError(
                            f"{f}: module '{name}' is listed more than once in `modules`"
                        )
                    seen.add(name)
                    versions[(feature_dir.name, name, _major_of(version))] = version
    return versions


def _require_manifest_content(manifest_versions, available_modules):
    missing = sorted(k for k in manifest_versions if k not in available_modules)
    if missing:
        details = ", ".join(f"{feat}/{mod} (major {maj})" for feat, mod, maj in missing)
        raise ValueError(
            f"params manifest names modules with no matching content directory: "
            f"{details}. Add the module's v<major> directory (with a .md), or "
            "correct the manifest version."
        )


def collect_v2_records(prompts_v2_dir):
    items = []
    manifest_versions = _collect_manifest_versions(prompts_v2_dir)
    available_modules = set()
    features_dir = prompts_v2_dir / "features"
    if features_dir.exists():
        for feature_dir in sorted(features_dir.iterdir()):
            if not feature_dir.is_dir():
                continue
            for module_dir in sorted(feature_dir.iterdir()):
                if not module_dir.is_dir():
                    continue
                for version_dir in sorted(module_dir.iterdir()):
                    if not version_dir.is_dir():
                        continue
                    records = _collect_v2_module_records(
                        version_dir,
                        feature_dir.name,
                        module_dir.name,
                        version_dir.name,
                        manifest_versions,
                    )
                    items.extend(records)
                    major = _major_of(version_dir.name)
                    if module_dir.name != "params" and records and major is not None:
                        available_modules.add((feature_dir.name, module_dir.name, major))

    _require_manifest_content(manifest_versions, available_modules)

    skills_dir = prompts_v2_dir / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            for version_dir in sorted(skill_dir.iterdir()):
                if not version_dir.is_dir():
                    continue
                items.extend(
                    _collect_v2_skill_records(version_dir, skill_dir.name, version_dir.name)
                )

    return items


def _collect_v2_module_records(version_dir, feature, module, version, manifest_versions):
    if module == "params":
        return _collect_v2_params_records(version_dir, feature, version)

    record_version = manifest_versions.get(
        (feature, module, _major_of(version)), _module_version(version)
    )

    items = []
    for stem, paths in sorted(_pair_files_by_stem(version_dir).items()):
        md_path = paths.get(".md")
        if md_path is None:
            continue
        items.append(
            {
                "id": f"{feature}--{module}--{_normalize_model(stem)}--{version}",
                "kind": "module",
                "feature": feature,
                "module": module,
                "model": stem,
                "version": record_version,
                "prompts": md_path.read_text(),
            }
        )
    return items


PARAMS_RESERVED_KEYS = frozenset({"id", "kind", "feature", "model"})


def _collect_v2_params_records(version_dir, feature, version):
    items = []
    for f in sorted(version_dir.iterdir()):
        if not f.is_file() or f.suffix != ".json":
            continue
        json_data = _read_json_if_exists(f)
        if not json_data:
            continue
        stem = f.stem
        conflicts = PARAMS_RESERVED_KEYS & set(json_data)
        if conflicts:
            raise ValueError(
                f"{f}: params JSON contains reserved key(s) {sorted(conflicts)} "
                "which would clobber the record's computed identity fields; "
                "remove them from the params file."
            )
        this_record = {
            **json_data,
            "id": f"{feature}--params--{_normalize_model(stem)}--{version}",
            "kind": "params",
            "feature": feature,
            "model": stem,
        }
        if isinstance(this_record.get("parameters"), dict):
            this_record["parameters"] = json.dumps(this_record["parameters"])
        if isinstance(this_record.get("model_details"), dict):
            this_record["model_details"] = json.dumps(this_record["model_details"])

        items.append(this_record)
    return items


def _collect_v2_skill_records(version_dir, name, version):
    items = []
    for stem, paths in sorted(_pair_files_by_stem(version_dir).items()):
        md_path = paths.get(".md")
        if md_path is None:
            continue
        json_data = _read_json_if_exists(paths.get(".json"))
        items.append(
            {
                "id": f"skill--{name}--{_normalize_model(stem)}--{version}",
                "kind": "skill",
                "name": name,
                "model": stem,
                "version": _module_version(version),
                "description": json_data.get("description", ""),
                "prompts": md_path.read_text(),
            }
        )
    return items


# ---------------------------------------------------------------------------
# Building


def _collectors():
    """The updater's collectors when it's installed, else the copies above."""
    try:
        from ai_window_prompts_updater import (
            collect_prompts_and_params as updater_v1,
            collect_v2_records as updater_v2,
        )
    except ImportError:
        return collect_prompts_and_params, collect_v2_records, False
    return updater_v1, updater_v2, True


def build_records(repo_path: Path) -> tuple[list[dict], bool]:
    prompts_dir = repo_path / "prompts"
    prompts_v2_dir = repo_path / "prompts_v2"
    if not prompts_dir.exists() and not prompts_v2_dir.exists():
        raise SystemExit(f"{repo_path} has no prompts/ or prompts_v2/ directory")

    v1, v2, from_updater = _collectors()
    records = v1(prompts_dir) if prompts_dir.exists() else []
    if prompts_v2_dir.exists():
        records.extend(v2(prompts_v2_dir))
    return records, from_updater


def export_ref(repo_path: Path, ref: str) -> Path:
    """Check `ref` out into a temp dir (read-only; the working tree is untouched)."""
    dest = Path(tempfile.mkdtemp(prefix="rs-prompts-")) / "repo"
    dest.mkdir()
    archive = subprocess.run(
        ["git", "-C", str(repo_path), "archive", ref],
        capture_output=True,
    )
    if archive.returncode != 0:
        shutil.rmtree(dest.parent, ignore_errors=True)
        raise SystemExit(
            f"git archive {ref} failed: {archive.stderr.decode(errors='replace').strip()}"
        )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest


def summarize(records: list[dict]) -> str:
    counts: dict[str, int] = {}
    for r in records:
        key = r.get("feature") or f"skill:{r.get('name', '?')}"
        kind = r.get("kind", "v1")
        counts[f"{key} ({kind})"] = counts.get(f"{key} ({kind})", 0) + 1
    return "\n".join(f"  {k:<48} {v:>3}" for k, v in sorted(counts.items()))


SNIPPET_TEMPLATE = """\
// Paste this whole block into the Browser Console (Cmd+Shift+J) of a Firefox
// running a throwaway profile, BEFORE opening the AI Window -- an AI Window
// that is already open keeps the configs its engine loaded at startup.
//
// Set these prefs in about:config first:
//   services.settings.server = http://127.0.0.1:1/v1   (unreachable, so prod
//       Remote Settings cannot silently clobber this import mid-session)
//   devtools.chrome.enabled  = true
//
// Built __BUILT_AT__ from __SOURCE__
__REF_COMMENT__(async () => {
  const path = __PATH__;
  const { RemoteSettings } = ChromeUtils.importESModule(
    "resource://services-settings/remote-settings.sys.mjs"
  );
  const client = RemoteSettings(__COLLECTION__);

  const text =
    typeof IOUtils !== "undefined"
      ? await IOUtils.readUTF8(path)
      : await (await fetch("file://" + path)).text();
  const records = JSON.parse(text);

  // clear:true drops the shipped/prod records in the same transaction -- a
  // prod record with a higher version would otherwise shadow the branch's.
  // The timestamp has to beat the packaged dump's, or the next client.get()
  // decides the local DB is stale and re-imports the dump over this data.
  const now = Date.now();
  await client.db.importChanges(
    {},
    now,
    records.map(r => ({ last_modified: now, ...r })),
    { clear: true }
  );

  const stored = await client.get();
  console.log(`imported ${records.length} records, client.get() sees ${stored.length}`);
  console.table(
    stored.map(r => ({
      id: r.id,
      kind: r.kind ?? "v1",
      feature: r.feature ?? r.name,
      module: r.module ?? "",
      model: r.model,
      version: r.version,
    }))
  );
})();
"""


def render_snippet(records_path: Path, built_at: str, source: str, ref: str | None) -> str:
    return (
        SNIPPET_TEMPLATE.replace("__BUILT_AT__", built_at)
        .replace("__SOURCE__", source)
        .replace("__REF_COMMENT__", f"// Git ref: {ref}\n" if ref else "")
        .replace("__PATH__", json.dumps(str(records_path)))
        .replace("__COLLECTION__", json.dumps(COLLECTION))
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile prompts into Remote Settings records for local Firefox testing."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=REPO_ROOT,
        help="prompts repo checkout to build from (default: this one)",
    )
    parser.add_argument(
        "--ref",
        help="build from this git ref instead of the working tree (e.g. origin/my-branch)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "build" / "prompt-records.json",
        help="records JSON output path (default: build/prompt-records.json)",
    )
    parser.add_argument(
        "--snippet",
        type=Path,
        default=None,
        help="Browser Console snippet output path (default: <out dir>/import-prompts.js)",
    )
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        metavar="NAME",
        help="only keep records for this feature or skill name (repeatable)",
    )
    args = parser.parse_args(argv)

    repo_path = args.repo.resolve()
    temp_root = None
    if args.ref:
        build_path = export_ref(repo_path, args.ref)
        temp_root = build_path.parent
        source = f"{repo_path} @ {args.ref}"
    else:
        build_path = repo_path
        source = str(repo_path)

    try:
        records, from_updater = build_records(build_path)
    finally:
        if temp_root:
            shutil.rmtree(temp_root, ignore_errors=True)

    if args.feature:
        wanted = set(args.feature)
        records = [r for r in records if (r.get("feature") or r.get("name")) in wanted]
        if not records:
            raise SystemExit(f"no records matched --feature {', '.join(sorted(wanted))}")

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(records, indent=2) + "\n")

    snippet = (args.snippet or out.parent / "import-prompts.js").resolve()
    snippet.parent.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    snippet.write_text(render_snippet(out, built_at, source, args.ref))

    print(f"{len(records)} records -> {out} ({out.stat().st_size / 1024:.0f} KB)")
    print(summarize(records))
    print(
        "\nrecord logic: "
        + ("installed ai_window_prompts_updater" if from_updater else "local copy in this script")
    )
    print(f"\nNext: set the two prefs from the header of {snippet}, then paste it")
    print("into the Browser Console (Cmd+Shift+J) before opening the AI Window.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
