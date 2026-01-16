import pytest
import json
import subprocess
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

def test_directory_structure():
    """Test that prompts directory has correct structure: feature/version/files"""
    assert PROMPTS_DIR.exists(), f"Prompts directory does not exist: {PROMPTS_DIR}"

    for feature_dir in PROMPTS_DIR.iterdir():
        assert feature_dir.is_dir(), f"{PROMPTS_DIR} contains non-directory file: {feature_dir}"

        for major_version_dir in feature_dir.iterdir():
            assert major_version_dir.is_dir(), f"{feature_dir} contains non-directory file: {major_version_dir}"

            # Check that version directories follow naming convention (e.g., v1, v2)
            assert major_version_dir.name.startswith("v"), \
                f"Version directory should start with 'v': {major_version_dir.name}"


def test_paired_files_exist():
    """Test that each model has both .json and .md files"""
    for feature_dir in PROMPTS_DIR.iterdir():
        if not feature_dir.is_dir():
            continue

        for major_version_dir in feature_dir.iterdir():
            if not major_version_dir.is_dir():
                continue

            files_by_stem = {}
            for f in major_version_dir.iterdir():
                if f.is_file():
                    files_by_stem.setdefault(f.stem, []).append(f.suffix)

            # Each model should have both .json and .md
            for model_name, suffixes in files_by_stem.items():
                assert ".json" in suffixes, \
                    f"Missing .json file for {model_name} in {major_version_dir}"
                assert ".md" in suffixes, \
                    f"Missing .md file for {model_name} in {major_version_dir}"
                assert len(suffixes) == 2, \
                    f"Unexpected files for {model_name} in {major_version_dir}: {suffixes}"

def test_json_files_valid():
    """Test that all JSON files are valid and parseable"""
    for feature_dir in PROMPTS_DIR.iterdir():
        if not feature_dir.is_dir():
            continue

        for major_version_dir in feature_dir.iterdir():
            if not major_version_dir.is_dir():
                continue

            for fi in major_version_dir.iterdir():
                if fi.suffix != ".json":
                    continue

                try:
                    with open(fi, "r") as f:
                        data = json.load(f)
                    assert isinstance(data, dict), f"JSON file should contain an object: {fi}"
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {fi}: {e}")
                except Exception as e:
                    pytest.fail(f"Error reading {fi}: {e}")

def test_json_required_fields():
    """Test that all JSON files contain required fields"""
    required_fields = ["feature", "version", "model", "is_default", "parameters", "additional_components"]

    for feature_dir in PROMPTS_DIR.iterdir():
        if not feature_dir.is_dir():
            continue

        for major_version_dir in feature_dir.iterdir():
            if not major_version_dir.is_dir():
                continue

            for fi in major_version_dir.iterdir():
                if fi.suffix != ".json":
                    continue

                with open(fi, "r") as f:
                    data = json.load(f)

                for field in required_fields:
                    assert field in data, f"Missing required field '{field}' in {fi}"

                # Validate field types
                assert isinstance(data["feature"], str), f"'feature' must be a string in {fi}"
                assert isinstance(data["version"], str), f"'version' must be a string in {fi}"
                assert isinstance(data["model"], str), f"'model' must be a string in {fi}"
                assert isinstance(data["is_default"], bool), f"'is_default' must be a boolean in {fi}"
                assert isinstance(data["parameters"], dict), f"'parameters' must be an object in {fi}"
                assert isinstance(data["additional_components"], list), f"'additional_components' must be an array in {fi}"


def test_feature_name_matches_directory():
    """Test that the feature field in JSON matches the directory name"""
    for feature_dir in PROMPTS_DIR.iterdir():
        if not feature_dir.is_dir():
            continue

        for major_version_dir in feature_dir.iterdir():
            if not major_version_dir.is_dir():
                continue

            for fi in major_version_dir.iterdir():
                if fi.suffix != ".json":
                    continue

                with open(fi, "r") as f:
                    data = json.load(f)

                assert data["feature"] == feature_dir.name, \
                    f"Feature name '{data['feature']}' doesn't match directory '{feature_dir.name}' in {fi}"


def test_markdown_files_not_empty():
    """Test that all .md files have content"""
    for feature_dir in PROMPTS_DIR.iterdir():
        if not feature_dir.is_dir():
            continue

        for major_version_dir in feature_dir.iterdir():
            if not major_version_dir.is_dir():
                continue

            for fi in major_version_dir.iterdir():
                if fi.suffix != ".md":
                    continue

                content = fi.read_text().strip()
                assert len(content) > 0, f"Markdown file is empty: {fi}"


def test_version_changed_from_main():
    """Test that version is different from main branch when files change"""
    try:
        # Get the default branch name (usually 'main' or 'master')
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "main"],
            cwd=PROMPTS_DIR.parent,
            capture_output=True,
            text=True
        )

        # Get list of changed files compared to base branch
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            cwd=PROMPTS_DIR.parent,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Git diff failed: {result.stderr}")

        changed_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        if not changed_files or changed_files == ['']:
            pytest.skip("No changed files compared to main branch")

        # Group changed files by their base name (without extension)
        prompts_changed = {}
        for file_path in changed_files:
            if not file_path.startswith("prompts/"):
                continue

            path = Path(file_path)
            if path.suffix in [".md", ".json"]:
                key = str(path.parent / path.stem)
                if key not in prompts_changed:
                    prompts_changed[key] = {"md": False, "json": False}
                if path.suffix == ".md":
                    prompts_changed[key]["md"] = True
                elif path.suffix == ".json":
                    prompts_changed[key]["json"] = True

        # For each changed file, verify the version is different from main
        for base_path, changes in prompts_changed.items():
            json_path = PROMPTS_DIR.parent / f"{base_path}.json"

            if changes["md"] or changes["json"]:
                # At least one file changed, verify JSON also changed
                assert changes["json"], \
                    f"File {base_path}.md changed but {base_path}.json was not updated"

                # Get the version from main branch
                try:
                    result = subprocess.run(
                        ["git", "show", f"main:{base_path}.json"],
                        cwd=PROMPTS_DIR.parent,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    old_data = json.loads(result.stdout)
                    old_version = old_data.get("version")
                except subprocess.CalledProcessError:
                    # File is new in this branch, no version to compare - this is OK
                    continue

                # Get the current version
                with open(json_path, "r") as f:
                    new_data = json.load(f)
                    new_version = new_data.get("version")

                # Only validate version change if the file existed in main
                if old_version is not None:
                    assert new_version is not None, f"Version missing in current branch for {base_path}.json"
                    assert old_version != new_version, \
                        f"Version unchanged from main branch in {base_path}.json: {old_version}"

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Git command failed: {e.cmd} - {e.stderr}")