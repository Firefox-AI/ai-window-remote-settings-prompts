#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from typing import Set, Tuple
from pathlib import PurePosixPath


def extract_pairs(files):
    pairs = set()
    for f in files:
        p = PurePosixPath(f)
        if len(p.parts) == 4 and p.parts[0] == "prompts" and p.suffix in (".json", ".md"):
            feature = p.parts[1]
            version = p.parts[2]
            model_name = p.stem
            pairs.add((feature, model_name, version))
    return sorted(pairs)


def git_changed_files(before: str, after: str):
    out = subprocess.check_output(["git", "diff", "--name-only", before, after], text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--env", default="DEV")  # DEV or PROD
    ap.add_argument("--bucket", default="main-workspace")
    ap.add_argument("--collection", default="ai-window-prompts")
    ap.add_argument("--request-review", action="store_true")
    args = ap.parse_args()

    changed = git_changed_files(args.before, args.after)
    print("Files changed: ", "\n- ".join(changed))
    pairs = sorted(extract_pairs(changed))

    if not pairs:
        print("No prompt changes detected; exiting.")
        return

    print("Changed pairs:")
    for feature, model_name, version in pairs:
        print(f" - {feature}/{model_name} - {version}")

    # Run your existing script once per pair
    for feature, model_name, version in pairs:
        cmd = [
            sys.executable, "remote_settings/push_to_remote_settings.py",
            "--env", args.env,
            "--bucket", args.bucket,
            "--collection", args.collection,
            "--feature", feature,
            "--model_name", model_name,
            "--version", version
        ]
        # Only request review ONCE at the very end (less churn)
        subprocess.check_call(cmd)

    if args.request_review:
        # Call once more on the last pair just to do the PATCH.
        # (Simplest: your push_one.py already knows how to PATCH.)
        feature, model_name, version = pairs[-1]
        cmd = [
            sys.executable, "remote_settings/push_to_remote_settings.py",
            "--env", args.env,
            "--bucket", args.bucket,
            "--collection", args.collection,
            "--feature", feature,
            "--model_name", model_name,
            "--version", version,
            "--request-review",
        ]
        subprocess.check_call(cmd)

if __name__ == "__main__":
    main()
