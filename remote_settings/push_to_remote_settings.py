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

def rs_request(method, url, token, json_body=None, extra_headers=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    resp = requests.request(method, url, headers=headers, json=json_body, timeout=60)
    return resp


def create_json_record(base, feature, model_name):
    with open(base / feature / f"{model_name}.json", "r") as f:
        json_blob = json.load(f)

    with open(base / feature / f"{model_name}.md", "r") as f:
        prompt = f.read().strip()
    
    json_blob["prompts"] = prompt
    major_version = json_blob["version"].split(".")[0]
    json_blob["id"] = f"{feature}--{model_name.replace('.', '-')}--v{major_version}"  # can't use .'s in ids
    json_blob['parameters'] = json.dumps(json_blob["parameters"])

    return json_blob


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
    record = create_json_record(base_path, args.feature, args.model_name)
    record_id = record["id"]

    base = server.rstrip("/")
    records_url = f"{base}/buckets/{args.bucket}/collections/{args.collection}/records"
    record_url = f"{records_url}/{record_id}"
    collection_url = f"{base}/buckets/{args.bucket}/collections/{args.collection}"

    print(records_url, collection_url)

    payload = {"data": record}

    # PUT-first upsert
    put_resp = rs_request("PUT", record_url, token, json_body=payload)

    if put_resp.status_code in (200, 201):
        # if no record exists, the system creates one
        action = "Created/Updated"
        print(f"{action} record id={record_id}")

    elif put_resp.status_code in (409, 412):
        # Optimistic concurrency: need If-Match with current last_modified
        get_resp = rs_request("GET", record_url, token)
        if get_resp.status_code != 200:
            print(f"GET existing record failed: {get_resp.status_code}\n{get_resp.text}", file=sys.stderr)
            sys.exit(1)

        existing = get_resp.json()["data"]
        last_modified = existing["last_modified"]

        put_resp2 = rs_request(
            "PUT",
            record_url,
            token,
            json_body=payload,
            extra_headers={"If-Match": str(last_modified)},
        )
        if put_resp2.status_code not in (200, 201):
            print(f"PUT (If-Match) failed: {put_resp2.status_code}\n{put_resp2.text}", file=sys.stderr)
            sys.exit(1)

        print(f"Updated record id={record_id}")

    else:
        print(f"PUT failed: {put_resp.status_code}\n{put_resp.text}", file=sys.stderr)
        sys.exit(1)



if __name__ == "__main__":
    main()




