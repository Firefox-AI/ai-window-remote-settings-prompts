# Handoff: Execute the Diff-Regression Evals-Repo Migration

**You are picking up where another session left off.** The plan is already written at `docs/superpowers/plans/2026-04-23-diff-regression-evals-repo.md`. Your job is to execute it.

---

## TL;DR

1. Read the plan in full: `docs/superpowers/plans/2026-04-23-diff-regression-evals-repo.md` (13 tasks).
2. Use the **superpowers:subagent-driven-development** skill to execute it task by task.
3. Implementation happens in **TWO repos**: most code goes in `/Users/mzhang/development/evals/`; only Tasks 10-11 touch this repo.
4. Credentials are in `/Users/mzhang/development/evals/.env` — use `set -a; . .env; set +a` to load (see caveat below).
5. A fresh git commit per task is fine; don't squash mid-execution.

---

## Current Repo State (as of this handoff)

**`ai-window-remote-settings-prompts` (this repo)**
- Branch: `diff-regression-eval-impl` (already created, checked out, do not switch)
- Contains **uncommitted hand-rolled eval code**: `evals/diff_regression/`, `tests/diff_regression/`, `evals/test_cases/`, `requirements-eval.txt`, `.github/workflows/diff-regression.yml`, `docs/superpowers/plans/*`
- That code is about to be deleted (Task 10). Don't commit it. Task 1 copies specific files from it into the evals repo.
- The stashed branch state (`fix-over-clarification` commits) is committed on that branch; you don't need to touch it.

**`/Users/mzhang/development/evals` (the destination)**
- Branch: whatever it's currently on (likely main or a feature branch) — create a feature branch before Task 1.
  ```bash
  cd /Users/mzhang/development/evals
  git checkout -b diff-regression-task
  ```
- Has a Python venv at `.venv/` — **use it**, do not create a new venv. The system Python lacks `fxa`, `google.cloud.secretmanager`, etc.
- Has its own `.env` with all credentials.

---

## Credentials and Environment

All credentials live in `/Users/mzhang/development/evals/.env`. **Important caveat**: that file has illustrative non-KEY=VALUE content (curl examples) starting around line 22, so naive `source` fails. Use:

```bash
set -a; . /Users/mzhang/development/evals/.env; set +a
```

`set -a` causes any variable assignment to be exported; the shell is tolerant of the non-assignment lines. Confirm with `echo "${FXA_EMAIL:0:5}"` (should print `mzhan`).

You will need these env vars for any MLPA-hitting task:
- `MLPA_TOKEN`, `FASTLY_TOKEN`, `FXA_EMAIL`, `FXA_PASSWORD`, `FXA_CLIENT_ID`, `OPENAI_API_KEY`
- For the diff-regression suite specifically: `DIFF_REGRESSION_BASELINE_PROMPT_PATH`, `DIFF_REGRESSION_CANDIDATE_PROMPT_PATH`, `DIFF_REGRESSION_OUTPUT_DIR`, `DIFF_REGRESSION_PR_BODY`
- For prompt loading from this repo: `REMOTE_PROMPTS_PATH=/Users/mzhang/development/ai-window-remote-settings-prompts`

---

## Execution Approach — Subagent-Driven

Invoke the skill at the start of the session:

```
Skill → superpowers:subagent-driven-development
```

For each task in the plan:

1. **Dispatch an implementer subagent** with the task's full text pasted in (not a link — subagents have no context from this conversation).
2. After they report DONE, **dispatch a spec-compliance reviewer** to confirm the code matches the task spec.
3. After that passes, **dispatch a code-quality reviewer**.
4. Mark task complete in TodoWrite; move to next.

The skill's prompt templates at `/Users/mzhang/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/skills/subagent-driven-development/` tell you the exact prompt shapes.

**Tasks that don't need deep review** (mechanical): 1 (copy files), 2 (copy judge prompt), 3 (build JSONL), 8 (write YAML). For these, a single implementer pass + a quick spec-check is enough.

**Tasks that need both reviews**: 4, 5, 6, 7 (the task class implementation). These are the real code.

**Task 9 and 12 are verification, not implementation** — run them yourself (or via a focused subagent that just executes the commands and reports output). If Task 9's smoke fails, iterate on 5/6/7 until it passes.

---

## Per-Task Caveats

**Task 1 (port modules):** The `sed -i '' 's|evals\.diff_regression|tasks.assistant.diff_regression|g'` replacement is macOS syntax. On Linux, drop the `''`. Also update test files that import `evals.diff_regression.*`.

**Task 3 (test_cases.jsonl):** Verify the row count is exactly 191 (20 incident + 171 cross_section). If different, check the source JSON files in `/Users/mzhang/development/ai-window-remote-settings-prompts/evals/test_cases/` — specifically the `samples` field on each case.

**Task 6 (`predict`):** The plan shows `kwargs["provider_instance"]` — the evals framework might pass this as `kwargs["provider"]` as a string or as an instance. **Check `utils/runner.py` run_task's func_kwargs contents** to confirm the exact key name before implementing. Adjust if needed.

**Task 7 (`eval` and `post_process_evals`):** The `llm_judge()` call expects a prompt with `!role:[system]` / `!role:[user]` markers (per `utils/metrics_llmjudge.py` line 15 uses `parse_messages`). Task 7's code includes them but if `parse_messages` fails, check the delimiter syntax.

**Task 8 (YAML):** Model name format is `provider:model_id`, e.g., `mlpa:gpt-oss-120b` and `openai:gpt-5`. Do NOT use `gpt-5` alone — MLPA won't route it.

**Task 9 (smoke run):** MLPA may be rate-limited depending on recent usage. If `task eval` hangs >2 min at the start, kill it and wait 2-3 min for TPM to recover. The framework handles 429s internally (60s backoff) but won't recover from a fully-exhausted daily quota.

**Task 10 (delete):** This deletes several hundred lines of code. Confirm Task 9 passed first. Verify the remaining `test.py` at this repo's root (prompt-structure validator) still passes via `pytest test.py -v` after the delete.

**Task 11 (GHA workflow):** The plan includes the full YAML. Just write it. Then verify secrets are set on the GitHub repo (`MLPA_TOKEN`, `FASTLY_TOKEN`, `FXA_EMAIL`, `FXA_PASSWORD`, `FXA_CLIENT_ID`, `OPENAI_API_KEY`, `EVALS_REPO_TOKEN`). If secrets aren't set yet, flag to the user — the workflow will fail silently otherwise.

**Task 12 (full run):** Uses 191 rows × 4 MLPA calls = ~760 calls. With the framework's account pool at `max_concurrency: 10`, expect ~5-8 min. This is the real "does fix-over-clarification regress vs main?" answer.

---

## Known Context from Prior Session (things you wouldn't otherwise know)

1. **Rate limit history**: Today's session burned significant per-user TPM. If your first MLPA call from this session stalls for >100s, that's the recovery window — the framework's 60s backoff handles it automatically, be patient.

2. **Empty responses**: gpt-oss-120b returns `content=None` on ~60% of tool-calling queries when no tools are declared in the API call. The task's predict() must declare tools (the plan does this via `provider.get_response(tools=...)`). If you see empty responses in Task 9, check that tools are being passed through.

3. **Judge model routing**: `openai:gpt-5` routes via OpenAI directly (bypasses MLPA). MLPA's `gpt-5` routing 400s. Task 4's `JudgeOutput` pydantic schema is designed for structured output via `response_format_model` in `llm_judge`.

4. **The `samples` field**: Each of the 61 original cases has a `samples` field (5 for incident, 3 for cross_section) defining how many times to re-run that case to beat temperature variance. The JSONL expansion (Task 3) flattens this: one row per `(case_id, sample_index)`.

5. **The `fix-over-clarification` branch**: That's the branch with the prompt fix being tested. It has the tab rule REMOVED. `main` has the tab rule present. For Task 12's run:
   - `baseline` = main (has tab rule) = the currently-shipped state
   - `candidate` = fix-over-clarification (no tab rule) = the proposed change
   - Expected: minimal regressions (fix is mostly an improvement), aggregation catches the "Your open tabs don't cover" prefix pattern only in baseline pool.

6. **Tests that need pytest-asyncio**: `test_mlpa_client.py` (now being moved) uses `@pytest.mark.asyncio`. The evals-repo venv has `pytest-asyncio` installed. No action needed, just be aware.

---

## When You Finish

1. Task 9 produced a smoke report at `/tmp/diff_regression_smoke/report.md`.
2. Task 10 deleted `evals/`, `tests/`, `requirements-eval.txt` from this repo.
3. Task 11 rewrote `.github/workflows/diff-regression.yml`.
4. Task 12 produced the real answer at `/tmp/diff_regression_full/report.md` — summarize it for the user.

Both repos should have their work committed (but not merged or pushed — user will handle PRs).

Report back to the user with:
- "Migration complete. All 13 tasks done."
- Summary of Task 12's report: did `fix-over-clarification` regress vs `main`? Cite specific flags if any.
- Any tasks that needed adjustment from the plan and why.

---

## If You Get Stuck

- **Subagent reports BLOCKED**: check the plan's task for the exact code; if the code doesn't match what they need, the plan has an error — fix the plan task and re-dispatch.
- **MLPA 429s persistently**: per-user quota exhausted. Pause for 5 min. If it persists, the user will need to cycle credentials.
- **Framework contract mismatch** (e.g., `predict` signature, `load_prompts` kwargs): the plan was based on a careful audit of `citation_mc_eval.py` and `utils/task_spec.py`, but the framework may have evolved. Re-read those files to find the current signature. Don't guess.
- **Tests fail after porting** (Task 1): likely the import rewrite missed something. Check for `from evals.diff_regression` or similar leftovers.

If truly stuck, escalate to the user with a specific question — don't invent.
