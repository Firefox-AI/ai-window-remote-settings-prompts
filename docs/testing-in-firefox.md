# Testing a branch's prompts in Firefox

Point a local Firefox at any branch of this repo without rebuilding it: compile
the branch into Remote Settings records, then import them into the profile's
`ai-window-prompts` collection from the Browser Console.

## 1. Compile the branch into records

```sh
python3 tools/build_rs_records.py                      # current checkout
python3 tools/build_rs_records.py --ref origin/my-branch   # another branch, working tree untouched
python3 tools/build_rs_records.py --feature aitab      # just one feature (smaller, easier to read)
```

Writes two files (default `build/`, which is gitignored):

- `prompt-records.json` — the records, exactly as the hourly updater would
  publish them (same IDs, same `parameters`/`model_details` JSON-string
  encoding, same manifest-stamped module versions).
- `import-prompts.js` — the Browser Console snippet for step 3, with the
  records path already baked in.

The script needs no dependencies. If
[`ai_window_prompts_updater`](https://github.com/mozilla/remote-settings-ai-window-prompts-updater)
happens to be installed it uses that package's collectors directly; otherwise it
uses its own copy of the same logic (which `test_v2.py` also mirrors). The last
line of the output says which one ran.

Don't use the updater's `fetch_current_prompts()` for this — it `rmtree`s the
parent of the path you hand it, since it's written for the cron's temp clone.

## 2. Launch Firefox with a throwaway profile

Set two prefs in `about:config`:

| Pref | Value | Why |
|---|---|---|
| `services.settings.server` | `http://127.0.0.1:1/v1` | Unreachable, so a background poll can't silently replace your import mid-session. |
| `devtools.chrome.enabled` | `true` | Needed for the Browser Console to evaluate privileged code. |

Use a scratch profile (`firefox --no-remote -P test` or `--profile /tmp/aiprof`)
— the import overwrites the collection in that profile's IndexedDB.

## 3. Import the records

Open the Browser Console (Cmd+Shift+J) **before** opening the AI Window, and
paste the contents of `build/import-prompts.js`. It clears the collection and
imports your records in one transaction, then prints a table of what's stored.

The AI Window reads `client.get()` when an engine loads its config and keeps a
cached client, so an AI Window that's already open keeps the configs it started
with. Import first, or close and reopen the window afterwards.

## 4. Verify what's being served

```js
const client = RemoteSettings("ai-window-prompts");
(await client.get())
  .filter(r => r.feature == "aitab")
  .map(r => `${r.kind} ${r.module ?? ""} ${r.model} v${r.version}`);
```

## Notes

- **It persists.** The records live in the profile's IndexedDB and survive
  restarts, as long as `services.settings.server` stays unreachable.
- **Two clobber paths, both handled by the snippet.** A successful sync against
  the real server overwrites the collection (hence the unreachable-server pref),
  and `client.get()` re-imports the packaged `ai-window-prompts.json` dump
  whenever the local timestamp is older than the dump's (hence importing with a
  `Date.now()` timestamp).
- **Back to normal:** reset `services.settings.server`, run
  `await RemoteSettings("ai-window-prompts").db.clear()`, and restart — or just
  throw the profile away.
- **Records are the whole collection.** Firefox picks per feature/major version
  out of everything it sees, so importing a `--feature`-filtered subset means
  other features fall back to their built-in defaults. Import the full set when
  testing anything beyond one feature.
