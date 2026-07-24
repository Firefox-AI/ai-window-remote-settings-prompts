import json
import re
from pathlib import Path

import pytest

PROMPTS_V2_DIR = Path(__file__).parent / "prompts_v2"
FEATURES_DIR = PROMPTS_V2_DIR / "features"
SKILLS_DIR = PROMPTS_V2_DIR / "skills"

# Keys the updater computes onto every params record (record identity). A params
# JSON that also defines them would clobber those fields, so they're forbidden.
PARAMS_RESERVED_KEYS = frozenset({"id", "kind", "feature", "model"})

# Manifest module versions must be "major.minor" (optionally v-prefixed), e.g.
# "1.0" — matching the updater's re.fullmatch check.
MODULE_VERSION_RE = re.compile(r"v?\d+\.\d+")


def _major_of(version_segment):
    """Major version (int) from 'v1', '1.0', '8.1', …; None when unparseable.

    Copied from the updater so the content-matching logic lines up exactly.
    """
    head = str(version_segment).lstrip("vV").split(".")[0]
    return int(head) if head.isdigit() else None


def _normalize_model(stem):
    """Model segment used in record IDs ('.' -> '-'), as the updater does."""
    return stem.replace(".", "-")


def _iter_feature_module_versions():
    """Yield (feature, module, version_dir) for every features/*/*/v# directory."""
    if not FEATURES_DIR.exists():
        return
    for feature_dir in sorted(FEATURES_DIR.iterdir()):
        if not feature_dir.is_dir():
            continue
        for module_dir in sorted(feature_dir.iterdir()):
            if not module_dir.is_dir():
                continue
            for version_dir in sorted(module_dir.iterdir()):
                if version_dir.is_dir():
                    yield feature_dir.name, module_dir.name, version_dir


def _iter_skill_versions():
    """Yield (skill_name, version_dir) for every skills/*/v# directory."""
    if not SKILLS_DIR.exists():
        return
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        for version_dir in sorted(skill_dir.iterdir()):
            if version_dir.is_dir():
                yield skill_dir.name, version_dir


def test_prompts_v2_top_level_structure():
    """Only features/ and skills/ are read; a stray/mistyped top-level dir
    (e.g. 'feature') would be silently ignored by the updater, so flag it."""
    assert PROMPTS_V2_DIR.exists(), f"prompts_v2 directory not found: {PROMPTS_V2_DIR}"

    for child in PROMPTS_V2_DIR.iterdir():
        if not child.is_dir():
            continue  # stray files (README, etc.) are harmless
        assert child.name in {
            "features",
            "skills",
        }, f"Unexpected top-level directory (the updater only reads features/ and skills/): {child}"


def test_v2_json_files_are_valid_objects():
    """Every JSON file must be a parseable object. The updater json.load()s
    these; a broken or non-object (or empty) file crashes ingestion."""
    json_files = list(PROMPTS_V2_DIR.rglob("*.json"))
    assert json_files, "expected at least one JSON file under prompts_v2"

    for jf in json_files:
        try:
            data = json.loads(jf.read_text())
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in {jf}: {e}")
        assert isinstance(data, dict), f"JSON file must contain an object: {jf}"


def test_v2_version_dirs_are_parseable():
    """Every version directory name must yield a numeric major (v1, v10, …).
    An unparseable name silently mis-versions a record and breaks manifest
    content-matching (major would be None)."""
    checked = 0
    for _feature, _module, version_dir in _iter_feature_module_versions():
        checked += 1
        assert (
            _major_of(version_dir.name) is not None
        ), f"Version dir name is not parseable to a major version (expected like 'v1'): {version_dir}"
    for _name, version_dir in _iter_skill_versions():
        checked += 1
        assert (
            _major_of(version_dir.name) is not None
        ), f"Version dir name is not parseable to a major version (expected like 'v1'): {version_dir}"
    assert checked, "no version directories found under prompts_v2"


def test_v2_content_dirs_have_prompt_body():
    """Non-params module dirs and skill dirs must contain at least one .md.
    The updater only emits a record for a stem that has a .md, so a .md-less
    content dir produces nothing (and, if a manifest names it, fails later)."""
    for _feature, module, version_dir in _iter_feature_module_versions():
        if module == "params":
            continue
        assert list(
            version_dir.glob("*.md")
        ), f"Module directory has no .md prompt body: {version_dir}"

    for _name, version_dir in _iter_skill_versions():
        assert list(
            version_dir.glob("*.md")
        ), f"Skill directory has no .md prompt body: {version_dir}"


def test_v2_markdown_files_not_empty():
    """Prompt bodies must have content — an empty .md ships an empty prompt."""
    for md in PROMPTS_V2_DIR.rglob("*.md"):
        assert md.read_text().strip(), f"Markdown file is empty: {md}"


def test_v2_params_json_valid():
    """params JSONs must not use reserved identity keys, and 'parameters',
    when present, must be an object (the updater json.dumps() it)."""
    for _feature, module, version_dir in _iter_feature_module_versions():
        if module != "params":
            continue
        for jf in sorted(version_dir.glob("*.json")):
            data = json.loads(jf.read_text())

            conflicts = PARAMS_RESERVED_KEYS & set(data)
            assert not conflicts, (
                f"{jf}: params JSON contains reserved key(s) {sorted(conflicts)} "
                "that would clobber the record's computed identity fields; remove them."
            )

            if "parameters" in data:
                assert isinstance(
                    data["parameters"], dict
                ), f"{jf}: 'parameters' must be an object"


def test_v2_params_manifest_module_entries_wellformed():
    """Each `modules` entry needs a name and a 'major.minor' string version,
    with no duplicate names in a file — mirrors the updater's manifest parse."""
    for _feature, module, version_dir in _iter_feature_module_versions():
        if module != "params":
            continue
        for jf in sorted(version_dir.glob("*.json")):
            data = json.loads(jf.read_text())
            seen_names = set()
            for entry in data.get("modules", []):
                name = entry.get("name")
                version = entry.get("version")

                assert name, f"{jf}: a `modules` entry is missing 'name'"
                assert version is not None, f"{jf}: module '{name}' is missing 'version'"
                assert isinstance(version, str), (
                    f"{jf}: module '{name}' version {version!r} must be a string "
                    '(quote it in JSON, e.g. "1.0" not 1.0)'
                )
                assert MODULE_VERSION_RE.fullmatch(version), (
                    f"{jf}: module '{name}' version '{version}' must be "
                    "'major.minor' (e.g. '1.0')"
                )
                assert (
                    name not in seen_names
                ), f"{jf}: module '{name}' is listed more than once in `modules`"
                seen_names.add(name)


def test_v2_manifest_modules_have_matching_content():
    """Every (feature, module, major) a params manifest names must have a
    content directory with a .md — the updater raises at publish time otherwise."""
    # Build available content the same way the updater populates available_modules:
    # non-params module dirs that have a parseable major and at least one .md.
    available = set()
    for feature, module, version_dir in _iter_feature_module_versions():
        if module == "params":
            continue
        major = _major_of(version_dir.name)
        if major is not None and list(version_dir.glob("*.md")):
            available.add((feature, module, major))

    missing = []
    for feature, module, version_dir in _iter_feature_module_versions():
        if module != "params":
            continue
        for jf in sorted(version_dir.glob("*.json")):
            data = json.loads(jf.read_text())
            for entry in data.get("modules", []):
                name = entry.get("name")
                version = entry.get("version")
                # Malformed entries are the previous test's job; skip them here.
                if not name or not isinstance(version, str):
                    continue
                major = _major_of(version)
                if (feature, name, major) not in available:
                    missing.append(
                        f"{jf}: names module '{name}' v{version}, but there is no "
                        f"features/{feature}/{name}/v{major}/ directory with a .md"
                    )

    assert (
        not missing
    ), "params manifests reference modules with no matching content:\n" + "\n".join(missing)


def test_v2_record_ids_unique():
    """The IDs the updater computes must be unique across the whole tree —
    a collision silently overwrites one record in Remote Settings."""
    ids = {}

    def claim(record_id, source):
        assert (
            record_id not in ids
        ), f"Duplicate record id '{record_id}': produced by both {ids[record_id]} and {source}"
        ids[record_id] = source

    for feature, module, version_dir in _iter_feature_module_versions():
        vname = version_dir.name
        if module == "params":
            for jf in sorted(version_dir.glob("*.json")):
                if not json.loads(jf.read_text()):
                    continue  # empty params JSON emits no record
                claim(f"{feature}--params--{_normalize_model(jf.stem)}--{vname}", jf)
        else:
            for md in sorted(version_dir.glob("*.md")):
                claim(f"{feature}--{module}--{_normalize_model(md.stem)}--{vname}", md)

    for name, version_dir in _iter_skill_versions():
        vname = version_dir.name
        for md in sorted(version_dir.glob("*.md")):
            claim(f"skill--{name}--{_normalize_model(md.stem)}--{vname}", md)
