import json
import os
import sys
from pathlib import Path
import argparse

import requests


DEV_SERVER = "https://remote-settings-dev.allizom.org/v1"
PROD_SERVER = "https://firefox.settings.services.mozilla.com/v1"

SERVER_LOOKUP = {
    "DEV": DEV_SERVER,
    "PROD": PROD_SERVER
}

def rs_request(method, url, token, json_body=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.request(method, url, headers=headers, json=json_body, timeout=60)
    return resp


def create_json_record(base, feature, model_name):
    with open(base / feature / f"{model_name}.json", "r") as f:
        json_blob = json.load(f)

    with open(base / feature / f"{model_name}.md", "r") as f:
        prompt = f.read().strip()
    
    json_blob["prompts"] = prompt
    major_version = json_blob["version"].split(".")[0]
    json_blob['parameters'] = json.dumps(json_blob["parameters"])

    return json_blob, f"{feature}--{model_name}--v{major_version}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", default="main-workspace") 
    ap.add_argument("--collection", default="ai-window-prompts")
    ap.add_argument("--env", default="DEV") # DEV, PROD
    ap.add_argument("--request-review", action="store_true")
    ap.add_argument("--feature", required=True)
    ap.add_argument("--model_name", required=True)
    args = ap.parse_args()

    ENV = args.env.upper()
    token = os.environ.get(f"RS_TOKEN_{ENV}")

    server = SERVER_LOOKUP.get(ENV, DEV_SERVER)

    if not token:
        print(f"Missing RS_TOKEN_{args.env} in env", file=sys.stderr)
        sys.exit(2)

    base_path = Path("./prompts")
    record, record_id = create_json_record(base_path, args.feature, args.model_name)

    base = server.rstrip("/")
    records_url = f"{base}/buckets/{args.bucket}/collections/{args.collection}/records"
    record_url = f"{records_url}/{record_id}"
    collection_url = f"{base}/buckets/{args.bucket}/collections/{args.collection}"

    print(records_url, collection_url)

    # Try create (POST). If it already exists, update (PUT).
    # POST requires wrapper {"data": {...}}.
    post_resp = rs_request("POST", records_url, token, json_body={"data": record})

    if post_resp.status_code in (200, 201):
        print(f"Created record id={record_id}")
    elif post_resp.status_code == 409:
        put_resp = rs_request("PUT", record_url, token, json_body={"data": record})
        if put_resp.status_code not in (200, 201):
            print(f"PUT failed: {put_resp.status_code}\n{put_resp.text}", file=sys.stderr)
            sys.exit(1)
        print(f"Updated record id={record_id}")
    else:
        print(f"POST failed: {post_resp.status_code}\n{post_resp.text}", file=sys.stderr)
        sys.exit(1)

    if args.request_review:
        patch_resp = rs_request("PATCH", collection_url, token, json_body={"data": {"status": "to-review"}})
        if patch_resp.status_code not in (200, 201):
            print(f"PATCH failed: {patch_resp.status_code}\n{patch_resp.text}", file=sys.stderr)
            sys.exit(1)
        print("Requested review: collection moved to to-review")


if __name__ == "__main__":
    main()




