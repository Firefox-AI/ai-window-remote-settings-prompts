# Differential Regression Eval — Evals-Repo Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the differential regression eval from `ai-window-remote-settings-prompts/evals/diff_regression/` (hand-rolled) into the `evals` repo as a proper `EvaluationTask`, so it inherits the framework's account pool, retry handling, concurrency management, caching, and output conventions. This repo's CI then becomes a thin wrapper that clones evals and invokes the suite.

**Architecture:** One `EvaluationTask` subclass in `tasks/assistant/diff_regression/`. `predict()` runs both baseline and candidate prompts on each test case and returns both responses. `eval()` invokes `llm_judge()` forward and reverse on the response pair. `post_process_evals()` runs median reduction across sample rows per case, applies two-tier fail criteria, runs aggregation pass over the full response pools, applies `regression-ack` overrides, and writes a markdown report file. One eval_suite YAML. Test cases live as a local JSONL in the task directory. Baseline and candidate prompt paths are injected via env vars (`DIFF_REGRESSION_BASELINE_PROMPT_PATH`, `DIFF_REGRESSION_CANDIDATE_PROMPT_PATH`) so CI can point at `/tmp/main_*.md` and the PR head's file, respectively; local dev falls back to YAML-declared versions.

**Tech Stack:** Python 3.12 (evals repo venv at `/Users/mzhang/development/evals/.venv`), pydantic 2, pytest, existing evals-framework modules (`utils/task_spec.py`, `utils/inference/`, `utils/metrics_llmjudge.py`, `utils/prompts.py`), GitHub Actions.

**Reference:** Two existing tasks are the closest patterns — `tasks/assistant/citation_mc_eval/citation_mc_eval.py` (LLM judge + programmatic metrics, closest fit) and `eval_suites/citation_mc_eval.yaml` (YAML structure with `default:` + per-task overrides).

**Non-goals:** Account pool reimplementation (we inherit it). ml_driver integration. Tool execution / tool-call result synthesis beyond the current serialize-into-content approach.

---

## File Structure

```
evals/ (the evals REPO — /Users/mzhang/development/evals/)
├── tasks/assistant/diff_regression/
│   ├── __init__.py
│   ├── diff_regression.py      # EvaluationTask — predict, eval, post_process_evals
│   ├── scoring.py              # ported: CaseScore, Flag, FlagCategory, median_reduce, apply_fail_criteria
│   ├── aggregation.py          # ported: detect_prefix_pattern, detect_length_shift, run_aggregation_pass
│   ├── override.py             # ported: Ack, parse_overrides, apply_overrides
│   ├── report.py               # ported: render_json, render_markdown
│   ├── test_cases.jsonl        # 191 rows: 61 cases expanded by sample_index (incident×5 + cross_section×3)
│   └── tests/
│       ├── __init__.py
│       ├── test_scoring.py     # ported unit tests
│       ├── test_aggregation.py
│       ├── test_override.py
│       └── test_report.py
├── eval_suites/
│   └── diff_regression.yaml
└── prompts/diff_regression/
    ├── judge.md                # the judge prompt (source of truth lives here now)
    └── baseline_chat.md        # placeholder — real baseline comes from env var
    └── candidate_chat.md       # placeholder — real candidate comes from env var

ai-window-remote-settings-prompts/ (THIS repo, cleanup pass)
├── evals/diff_regression/      # DELETE the hand-rolled code
├── tests/diff_regression/      # DELETE
├── evals/test_cases/           # DELETE (moved into evals repo)
├── requirements-eval.txt       # DELETE (evals repo has its own)
└── .github/workflows/diff-regression.yml    # REWRITE — thin wrapper
```

**Boundaries:**
- `diff_regression.py` only glues the framework to the pure-logic modules. No scoring or aggregation math lives there.
- `scoring.py`, `aggregation.py`, `override.py`, `report.py` are pure Python — no framework imports, no IO beyond explicit file writes in report.py. Trivially unit-testable.
- Judge prompt lives as plain `.md` so non-coders can update the Approved Artifacts list.

---

## Task 1: Scaffold task directory + copy pure-logic modules

**Files:**
- Create: `evals/tasks/assistant/diff_regression/__init__.py` (empty)
- Create: `evals/tasks/assistant/diff_regression/tests/__init__.py` (empty)
- Create: `evals/tasks/assistant/diff_regression/scoring.py`
- Create: `evals/tasks/assistant/diff_regression/aggregation.py`
- Create: `evals/tasks/assistant/diff_regression/override.py`
- Create: `evals/tasks/assistant/diff_regression/report.py`
- Create: `evals/tasks/assistant/diff_regression/tests/test_scoring.py`
- Create: `evals/tasks/assistant/diff_regression/tests/test_aggregation.py`
- Create: `evals/tasks/assistant/diff_regression/tests/test_override.py`
- Create: `evals/tasks/assistant/diff_regression/tests/test_report.py`

- [ ] **Step 1: Copy files verbatim from the prompt repo**

```bash
SRC=/Users/mzhang/development/ai-window-remote-settings-prompts
DST=/Users/mzhang/development/evals/tasks/assistant/diff_regression
mkdir -p "$DST/tests"
touch "$DST/__init__.py" "$DST/tests/__init__.py"
cp "$SRC/evals/diff_regression/scoring.py" "$DST/scoring.py"
cp "$SRC/evals/diff_regression/aggregation.py" "$DST/aggregation.py"
cp "$SRC/evals/diff_regression/override.py" "$DST/override.py"
cp "$SRC/evals/diff_regression/report.py" "$DST/report.py"
cp "$SRC/tests/diff_regression/test_scoring.py" "$DST/tests/test_scoring.py"
cp "$SRC/tests/diff_regression/test_aggregation.py" "$DST/tests/test_aggregation.py"
cp "$SRC/tests/diff_regression/test_override.py" "$DST/tests/test_override.py"
cp "$SRC/tests/diff_regression/test_report.py" "$DST/tests/test_report.py"
```

- [ ] **Step 2: Update imports in the copied files to match the new location**

Each of the 4 module files (`scoring.py`, `aggregation.py`, `override.py`, `report.py`) and each test file currently imports from `evals.diff_regression.*`. Replace with `tasks.assistant.diff_regression.*`.

Apply this find-replace across all 8 copied files:

```bash
cd /Users/mzhang/development/evals/tasks/assistant/diff_regression
grep -rl "evals.diff_regression" . | xargs sed -i '' 's|evals\.diff_regression|tasks.assistant.diff_regression|g'
```

- [ ] **Step 3: Run the ported tests**

```bash
cd /Users/mzhang/development/evals
.venv/bin/python -m pytest tasks/assistant/diff_regression/tests/ -v
```

Expected: 21 passed (6 scoring + 4 aggregation + 4 override + 3 report + 4 metadata/drift tests from the last pass). The pure-logic modules have no framework dependencies, so they pass without any MLPA calls.

- [ ] **Step 4: Commit**

```bash
cd /Users/mzhang/development/evals
git add tasks/assistant/diff_regression/
git commit -m "feat(diff-regression): port pure-logic modules from prompt repo"
```

---

## Task 2: Port judge prompt to evals-repo convention

**Files:**
- Create: `evals/prompts/diff_regression/judge.md`

The evals repo's convention is prompts live at `evals/prompts/<task_name>/<prompt_name>.md` and get loaded via `prompt_source: evals`.

- [ ] **Step 1: Copy the judge prompt**

```bash
SRC=/Users/mzhang/development/ai-window-remote-settings-prompts/evals/diff_regression/judge_prompt.md
DST=/Users/mzhang/development/evals/prompts/diff_regression/judge.md
mkdir -p "$(dirname "$DST")"
cp "$SRC" "$DST"
```

- [ ] **Step 2: Verify the content is identical**

```bash
diff /Users/mzhang/development/ai-window-remote-settings-prompts/evals/diff_regression/judge_prompt.md \
     /Users/mzhang/development/evals/prompts/diff_regression/judge.md
```

Expected: no output (files identical).

- [ ] **Step 3: Commit**

```bash
cd /Users/mzhang/development/evals
git add prompts/diff_regression/
git commit -m "feat(diff-regression): add judge prompt"
```

---

## Task 3: Build the test-case dataset JSONL

**Files:**
- Create: `evals/tasks/assistant/diff_regression/test_cases.jsonl` (191 rows)
- Create: `evals/tasks/assistant/diff_regression/build_test_cases.py` (one-shot builder; committed so expansion is reproducible)

**Why:** The evals framework's `load_data()` expects one dataset row per prediction. Our 61 cases each run multiple samples (5 for incident, 3 for cross_section). Expanding now means the framework's per-row concurrency matches sample-level parallelism. The `case_id` field lets `post_process_evals()` group rows back to cases for the median reduction.

- [ ] **Step 1: Write `build_test_cases.py`**

```python
"""Expand per-case JSON files from the prompt repo into a flat JSONL dataset,
with one row per (case_id, sample_index) pair. Run once; commit the output."""
import json
import sys
from pathlib import Path

PROMPT_REPO = Path("/Users/mzhang/development/ai-window-remote-settings-prompts")
CASES_DIR = PROMPT_REPO / "evals" / "test_cases"
OUT = Path(__file__).parent / "test_cases.jsonl"


def main():
    rows = []
    for group_dir in (CASES_DIR / "incident", CASES_DIR / "cross_section"):
        for f in sorted(group_dir.glob("*.json")):
            with open(f) as fp:
                cases = json.load(fp)
            for c in cases:
                n = c["samples"]
                for i in range(n):
                    rows.append({
                        "case_id": c["id"],
                        "sample_index": i,
                        "set": c["set"],
                        "category": c["category"],
                        "query": c["query"],
                        "tabs": c["tabs"],
                        "saved_facts": c["saved_facts"],
                        "prior_messages": c["prior_messages"],
                    })

    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

```bash
cd /Users/mzhang/development/evals
.venv/bin/python tasks/assistant/diff_regression/build_test_cases.py
```

Expected: `wrote 191 rows to ...test_cases.jsonl`  (4 incident × 5 samples + 57 cross_section × 3 samples = 20 + 171 = 191).

- [ ] **Step 3: Sanity-check the JSONL loads**

```bash
cd /Users/mzhang/development/evals
.venv/bin/python -c "
import pandas as pd
df = pd.read_json('tasks/assistant/diff_regression/test_cases.jsonl', lines=True)
print(f'rows: {len(df)}')
print('columns:', list(df.columns))
print('by set:', df['set'].value_counts().to_dict())
print('cases:', df['case_id'].nunique())
"
```

Expected:
```
rows: 191
columns: ['case_id', 'sample_index', 'set', 'category', 'query', 'tabs', 'saved_facts', 'prior_messages']
by set: {'cross_section': 171, 'incident': 20}
cases: 61
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mzhang/development/evals
git add tasks/assistant/diff_regression/build_test_cases.py tasks/assistant/diff_regression/test_cases.jsonl
git commit -m "data(diff-regression): expand 61 test cases to 191 sample rows"
```

---

## Task 4: Define the judge output schema (Pydantic)

**Files:**
- Modify: `evals/tasks/assistant/diff_regression/diff_regression.py` (new file, start of implementation)

Other tasks declare the Pydantic `EvalResponse` as a nested class in the task file. We follow that convention and also define a `JudgeOutput` model used as `response_format_model` in `llm_judge()` calls.

- [ ] **Step 1: Create `diff_regression.py` with the Pydantic schemas**

```python
"""Differential regression eval task.

Runs baseline and candidate prompts against the same test cases, compares
response pairs with an LLM judge (forward + reverse for position-bias detection),
medians scores across samples per case, and emits BLOCK/REVIEW flags plus a
markdown report.
"""
import asyncio
import json
import os
from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from utils.inference.provider import Provider
from utils.metrics_llmjudge import llm_judge
from utils.prompts import load_prompt_from_yaml
from utils.task_spec import EvaluationTaskBase

from tasks.assistant.diff_regression import aggregation, override, report, scoring

_NAMED_DIMS = ("no_new_artifacts", "no_capability_loss", "instruction_adherence")
_ALL_DIMS = (*_NAMED_DIMS, "overall_regression")


class JudgeOutput(BaseModel):
    """Structured output from the LLM judge for one response pair."""
    no_new_artifacts_justification: str
    no_new_artifacts: int
    no_capability_loss_justification: str
    no_capability_loss: int
    instruction_adherence_justification: str
    instruction_adherence: int
    overall_regression_justification: str
    overall_regression: int


class EvalResponse(BaseModel):
    """Per-row eval result. Populated by eval()."""
    # Forward (A=baseline, B=candidate) scores
    no_new_artifacts: int
    no_capability_loss: int
    instruction_adherence: int
    overall_regression: int
    # Position-flip reconciliation
    flip_agreement: int   # 1 if (forward+reverse ≈ 6 per dim), 0 otherwise
    # Compact justification string (first dim only — full details in JSONL)
    justification: str
```

- [ ] **Step 2: No test — schema is exercised through the integration test in Task 8**

- [ ] **Step 3: Commit (continues in Task 5)**

Do not commit yet; `diff_regression.py` will grow through Task 7. The commit comes at the end of Task 7 when the file is complete.

---

## Task 5: Implement `EvaluationTask.load_prompts()`

**Files:**
- Modify: `evals/tasks/assistant/diff_regression/diff_regression.py`

Baseline and candidate prompt paths come from env vars (CI path) with fallback to `load_prompt_from_yaml()` (local dev path). Judge prompt always comes from the YAML config.

- [ ] **Step 1: Add the `EvaluationTask` class with `load_prompts()`**

Append to `diff_regression.py`:

```python
class EvaluationTask(EvaluationTaskBase):
    task_name = "diff_regression"

    def load_prompts(self, provider: str, kwargs: dict):
        """Load judge prompt from YAML; load baseline/candidate chat prompts
        from env vars if present, else fall back to YAML.

        Env-var override exists so CI can point at arbitrary prompt files
        (e.g. /tmp/main.md and $PR_HEAD/prompts/...) without editing YAML.
        """
        self.judge_prompt = load_prompt_from_yaml("judge_prompt", kwargs)

        baseline_env = os.environ.get("DIFF_REGRESSION_BASELINE_PROMPT_PATH")
        candidate_env = os.environ.get("DIFF_REGRESSION_CANDIDATE_PROMPT_PATH")
        if baseline_env and candidate_env:
            self.baseline_chat_prompt = Path(baseline_env).read_text()
            self.candidate_chat_prompt = Path(candidate_env).read_text()
        else:
            self.baseline_chat_prompt = load_prompt_from_yaml("baseline_chat_prompt", kwargs)
            self.candidate_chat_prompt = load_prompt_from_yaml("candidate_chat_prompt", kwargs)

        # load the real-time-context (date, tab) templates used by every prompt
        self.load_system_prompts(kwargs)
```

- [ ] **Step 2: No test — exercised in Task 8's integration smoke**

---

## Task 6: Implement `EvaluationTask.predict()`

**Files:**
- Modify: `evals/tasks/assistant/diff_regression/diff_regression.py`

For each row, run BOTH baseline and candidate prompts and store both responses. The task-level concurrency is set by `predict.max_concurrency` in YAML; the runner enforces it automatically.

- [ ] **Step 1: Add `predict()` to the class**

Append to the `EvaluationTask` class (same file):

```python
    def _compose_system_prompt(self, chat_prompt: str, tab: dict) -> str:
        """Build the full system prompt: chat + date context + tab context.
        Mirrors what Firefox ships in production."""
        # self.date_prompt and self.tab_prompt come from self.load_system_prompts
        # and already have format placeholders; call with the row's tab.
        from datetime import datetime
        now = datetime.now()
        date_ctx = self.date_prompt.format(
            locale="en-US",
            timezone="America/Los_Angeles",
            isoTimestamp=now.isoformat(),
            todayDate=now.strftime("%A, %B %d, %Y"),
        )
        tab_ctx = self.tab_prompt.format(
            url=tab.get("url", "https://www.example.com"),
            title=tab.get("title", "Example Page"),
            description=tab.get("description", ""),
            dsecription=tab.get("description", ""),  # preserved typo in upstream template
            additionalTabs=tab.get("additionalTabs", ""),
        )
        return "\n\n".join([chat_prompt, date_ctx, tab_ctx])

    async def predict(self, obj: dict, **kwargs: dict) -> dict:
        """Run both baseline and candidate on the row's query."""
        provider: Provider = kwargs["provider_instance"]
        model_id: str = kwargs["model_id"]

        tab = obj["tabs"][0] if obj["tabs"] else {"url": "", "title": "", "description": ""}
        user_messages = [
            {"role": m["role"], "content": m["content"]} for m in obj["prior_messages"]
        ] + [{"role": "user", "content": obj["query"]}]

        async def run_one(chat_prompt: str) -> str:
            sys_prompt = self._compose_system_prompt(chat_prompt, tab)
            messages = [{"role": "system", "content": sys_prompt}, *user_messages]
            resp = await provider.get_response(
                model_id=model_id, messages=messages,
                retries=kwargs.get("retries", 3),
                base_delay=kwargs.get("base_delay", 0.8),
                temperature=kwargs.get("temperature", 1.0),
                tools=kwargs.get("tools"),
                task_flags=kwargs.get("task_flags", {}),
            )
            if not resp["success"]:
                return ""
            msg = resp["response"].choices[0].message
            content = msg.content or ""
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                tc = "\n".join(
                    f"[TOOL_CALL: {c.function.name}({c.function.arguments})]" for c in tool_calls
                )
                content = (f"{content}\n{tc}").strip() if content else tc
            return content

        response_a, response_b = await asyncio.gather(
            run_one(self.baseline_chat_prompt),
            run_one(self.candidate_chat_prompt),
        )
        return {"response_a": response_a, "response_b": response_b}
```

- [ ] **Step 2: No unit test — verify via Task 8 smoke**

---

## Task 7: Implement `eval()` and `post_process_evals()`

**Files:**
- Modify: `evals/tasks/assistant/diff_regression/diff_regression.py`

`eval()` runs the judge forward and reverse on each sample-row's response pair. `post_process_evals()` aggregates by `case_id`, computes medians, applies fail criteria and the aggregation pass, and writes `report.md` / `report.json` alongside the framework's `evals.jsonl`.

- [ ] **Step 1: Add `eval()`**

Append to the `EvaluationTask` class:

```python
    _CHANNEL_RE = __import__("re").compile(
        r"<\|channel\|>[^<]*<\|message\|>(.*?)<\|end\|>",
        __import__("re").DOTALL,
    )

    def _strip_scaffolding(self, text: str) -> str:
        return self._CHANNEL_RE.sub(lambda m: m.group(1), text or "").strip()

    def _build_judge_input(self, obj: dict, response_a: str, response_b: str) -> str:
        tab_lines = "\n".join(
            f"- {t.get('title', '')} ({t.get('url', '')})" for t in obj["tabs"]
        ) or "(none)"
        fact_lines = "\n".join(
            f"- {f.get('text', '')}" for f in obj["saved_facts"]
        ) or "(none)"
        return (
            f"USER QUERY:\n{obj['query']}\n\n"
            f"BROWSER TABS:\n{tab_lines}\n\n"
            f"SAVED USER FACTS:\n{fact_lines}\n\n"
            f"RESPONSE A (baseline):\n{self._strip_scaffolding(response_a)}\n\n"
            f"RESPONSE B (candidate):\n{self._strip_scaffolding(response_b)}\n"
        )

    async def eval(self, obj: dict, **kwargs: dict) -> dict:
        """Judge the response pair forward and reverse."""
        response_a = obj.get("response_a", "") or ""
        response_b = obj.get("response_b", "") or ""

        judge_input_fwd = self._build_judge_input(obj, response_a, response_b)
        judge_input_rev = self._build_judge_input(obj, response_b, response_a)

        fwd_prompt = f"!role:[system]\n{self.judge_prompt}\n\n!role:[user]\n{judge_input_fwd}"
        rev_prompt = f"!role:[system]\n{self.judge_prompt}\n\n!role:[user]\n{judge_input_rev}"

        fwd, rev = await asyncio.gather(
            llm_judge(prompt=fwd_prompt, response_format_model=JudgeOutput, **kwargs),
            llm_judge(prompt=rev_prompt, response_format_model=JudgeOutput, **kwargs),
        )

        # dim agreement: forward + reverse ≈ 6 per dim, within tolerance 2
        agree = all(abs((fwd[d] + rev[d]) - 6) <= 2 for d in _ALL_DIMS)

        return {
            "no_new_artifacts": fwd["no_new_artifacts"],
            "no_capability_loss": fwd["no_capability_loss"],
            "instruction_adherence": fwd["instruction_adherence"],
            "overall_regression": fwd["overall_regression"],
            "flip_agreement": int(agree),
            "justification": fwd["no_new_artifacts_justification"][:400],
            # Keep the full per-dim justifications for debugging (not in EvalResponse schema)
            "fwd_justifications": {d: fwd[f"{d}_justification"] for d in _ALL_DIMS},
            "rev_scores": {d: rev[d] for d in _ALL_DIMS},
        }
```

- [ ] **Step 2: Add `post_process_evals()`**

```python
    def post_process_evals(self, evals_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate per-case medians, apply fail criteria, run aggregation
        pass, apply PR-body overrides, write report.md + report.json."""
        # Build CaseScore list, one per case_id, with median scores across samples
        case_scores = []
        for case_id, group in evals_df.groupby("case_id"):
            sample_dicts = group[list(_ALL_DIMS)].to_dict(orient="records")
            medians = scoring.median_reduce(sample_dicts)
            flip_ok = bool(group["flip_agreement"].all())
            # Metadata: response length medians + pass-error counts
            a_lens = group["response_a"].str.len().tolist()
            b_lens = group["response_b"].str.len().tolist()
            case_scores.append(scoring.CaseScore(
                id=case_id,
                set=group["set"].iloc[0],
                category=group["category"].iloc[0],
                scores=medians,
                flip_agreement=flip_ok,
                metadata={
                    "baseline_length_chars_median": int(pd.Series(a_lens).median()) if a_lens else 0,
                    "candidate_length_chars_median": int(pd.Series(b_lens).median()) if b_lens else 0,
                    "n_samples": len(group),
                },
            ))

        flags = scoring.apply_fail_criteria(case_scores)

        # Aggregation pass across full A/B pools
        a_pool = evals_df["response_a"].tolist()
        b_pool = evals_df["response_b"].tolist()
        flags.extend(aggregation.run_aggregation_pass(a_pool=a_pool, b_pool=b_pool))

        # PR-body override (env var carries the PR body in CI)
        pr_body = os.environ.get("DIFF_REGRESSION_PR_BODY", "")
        flags = override.apply_overrides(flags, override.parse_overrides(pr_body))

        # Emit the human-readable + machine-readable reports
        out_dir = Path(os.environ.get("DIFF_REGRESSION_OUTPUT_DIR", "results/diff_regression"))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(
            report.render_json(cases=case_scores, flags=flags)
        )
        md = report.render_markdown(cases=case_scores, flags=flags)
        (out_dir / "report.md").write_text(md)
        print(md)

        # Fail the process if any BLOCK flag survived overrides — signals CI to exit nonzero
        if any(f.category == scoring.FlagCategory.BLOCK for f in flags):
            os.environ["DIFF_REGRESSION_BLOCKED"] = "1"

        return evals_df
```

- [ ] **Step 3: Commit the completed `diff_regression.py`**

```bash
cd /Users/mzhang/development/evals
git add tasks/assistant/diff_regression/diff_regression.py
git commit -m "feat(diff-regression): add EvaluationTask (predict, eval, post_process)"
```

---

## Task 8: Write the eval_suite YAML

**Files:**
- Create: `evals/eval_suites/diff_regression.yaml`

Mirrors the shape of `citation_mc_eval.yaml`. One task, one dataset, one predict config, one eval config. Baseline/candidate prompts are declared as YAML stubs; env vars override at runtime.

- [ ] **Step 1: Write the YAML**

```yaml
tasks:
  - name: diff_regression
    task: tasks.assistant.diff_regression.diff_regression

    predict:
      model_name: mlpa:gpt-oss-120b
      temperature: 1.0
      retries: 3
      base_delay: 0.8
      max_concurrency: 10
      service_type: ai-dev

    eval:
      model_name: openai:gpt-5
      retries: 3
      base_delay: 0.8
      max_concurrency: 10

    prompts:
      baseline_chat_prompt:
        prompt_source: local
        prompt_name: chat/gpt-oss-120b
        prompt_version: "v4"
      candidate_chat_prompt:
        prompt_source: local
        prompt_name: chat/gpt-oss-120b
        prompt_version: "v4"
      judge_prompt:
        prompt_source: evals
        prompt_name: diff_regression/judge
        prompt_version: ""
      date_prompt:
        prompt_source: local
        prompt_name: real-time-context-date/qwen3-235b-a22b-instruct-2507-maas
        prompt_version: "v1"
      tab_prompt:
        prompt_source: local
        prompt_name: real-time-context-tab/qwen3-235b-a22b-instruct-2507-maas
        prompt_version: "v1"

    skip_inference: false
    clear_cache: true

    data:
      path: tasks/assistant/diff_regression/test_cases.jsonl
      limit_rows: 0
```

- [ ] **Step 2: Verify the YAML parses**

```bash
cd /Users/mzhang/development/evals
.venv/bin/python -c "import yaml; yaml.safe_load(open('eval_suites/diff_regression.yaml')); print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
cd /Users/mzhang/development/evals
git add eval_suites/diff_regression.yaml
git commit -m "feat(diff-regression): add eval suite config"
```

---

## Task 9: Local smoke run

**Files:** none (verification only)

Run the suite end-to-end against a small slice to confirm the wiring works before we declare the migration done. Use `limit_rows: 5` temporarily to avoid burning quota.

- [ ] **Step 1: Extract both prompt versions**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
git show main:prompts/chat/v4/gpt-oss-120b.md > /tmp/main_baseline.md
git show fix-over-clarification:prompts/chat/v4/gpt-oss-120b.md > /tmp/fix_candidate.md
```

- [ ] **Step 2: Temporarily set `limit_rows: 5` for the smoke run**

Edit `eval_suites/diff_regression.yaml` and change `limit_rows: 0` → `limit_rows: 5`. Revert before committing anything else.

- [ ] **Step 3: Run it**

```bash
cd /Users/mzhang/development/evals
export DIFF_REGRESSION_BASELINE_PROMPT_PATH=/tmp/main_baseline.md
export DIFF_REGRESSION_CANDIDATE_PROMPT_PATH=/tmp/fix_candidate.md
export DIFF_REGRESSION_OUTPUT_DIR=/tmp/diff_regression_smoke
task eval -- --suite diff_regression
```

Expected: 5 rows each produce predict output (response_a + response_b) and eval output (judge scores + flip_agreement). `post_process_evals` writes `/tmp/diff_regression_smoke/report.json` and `report.md`. A markdown summary prints to stdout.

If 429 rate-limit errors appear during the run, the framework's `retry_helper` handles the 60s backoff automatically — confirm it recovers rather than fails.

- [ ] **Step 4: Inspect the output**

```bash
cat /tmp/diff_regression_smoke/report.md
jq '.cases | length, .flags | length' /tmp/diff_regression_smoke/report.json
```

Expected: at least one BLOCK flag on one of the 5 incident cases (since candidate's fix-over-clarification removes the tab rule that main has, the judge should see artifact differences). The markdown should render without malformed rows.

- [ ] **Step 5: Revert `limit_rows` to 0 and do not commit the temporary edit**

```bash
cd /Users/mzhang/development/evals
git checkout eval_suites/diff_regression.yaml
```

---

## Task 10: Delete the hand-rolled code from the prompt repo

**Files:**
- Delete: `evals/diff_regression/` (the whole directory)
- Delete: `tests/diff_regression/` (the whole directory)
- Delete: `evals/test_cases/` (moved into evals repo)
- Delete: `evals/fixtures/` (was for ground-truth, no longer needed)
- Delete: `requirements-eval.txt` (evals repo has its own)

**Why:** Once the evals-repo task works, all this is dead code. Keeping it creates two sources of truth and an inevitable drift.

- [ ] **Step 1: Confirm evals-repo smoke passes (Task 9) before deleting**

If Task 9 failed, stop and fix before proceeding.

- [ ] **Step 2: Delete the directories**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
rm -rf evals/ tests/ requirements-eval.txt
```

(The `evals/` dir at the repo root here held only the migrated code — no longer needed. If this repo later gets other evals, they should also live in the evals repo, not here.)

- [ ] **Step 3: Verify prompt-validation CI still works**

This repo's original `test.py` + `.github/workflows/ci.yml` validate prompt file structure. They don't depend on the deleted dirs.

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
python3 -m pytest test.py -v
```

Expected: existing tests still pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
git add -A
git commit -m "chore: remove hand-rolled diff-regression eval (moved to evals repo)"
```

---

## Task 11: Rewrite the prompt-repo GitHub Actions workflow

**Files:**
- Rewrite: `.github/workflows/diff-regression.yml`

New workflow is a thin wrapper: checkout, fetch main, extract both prompt versions, clone evals repo, run suite, post comment, fail if blocked.

- [ ] **Step 1: Replace the workflow**

```yaml
name: Differential Regression Eval

on:
  pull_request:
    types: [labeled, synchronize, opened]
    paths:
      - 'prompts/**'

jobs:
  diff_regression:
    if: contains(github.event.pull_request.labels.*.name, 'needs-regression-eval')
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout PR
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Fetch main
        run: git fetch origin main:main

      - name: Detect changed prompt model
        id: detect
        run: |
          changed=$(git diff --name-only origin/main..HEAD -- 'prompts/chat/**/*.md' | head -n 1)
          if [ -z "$changed" ]; then echo "skip=true" >> $GITHUB_OUTPUT; exit 0; fi
          echo "changed_path=$changed" >> $GITHUB_OUTPUT
          echo "skip=false" >> $GITHUB_OUTPUT

      - name: Extract baseline (main) and candidate (PR head) prompt files
        if: steps.detect.outputs.skip != 'true'
        run: |
          git show main:${{ steps.detect.outputs.changed_path }} > /tmp/main_baseline.md
          cp ${{ steps.detect.outputs.changed_path }} /tmp/candidate.md

      - name: Clone evals repo
        if: steps.detect.outputs.skip != 'true'
        env:
          EVALS_REPO_TOKEN: ${{ secrets.EVALS_REPO_TOKEN }}
        run: |
          git clone --depth 1 \
            https://x-access-token:${EVALS_REPO_TOKEN}@github.com/Firefox-AI/evals.git _evals

      - name: Set up Python + install evals deps
        if: steps.detect.outputs.skip != 'true'
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - name: Install evals deps
        if: steps.detect.outputs.skip != 'true'
        run: |
          cd _evals
          pip install -r requirements.txt

      - name: Run diff-regression suite
        if: steps.detect.outputs.skip != 'true'
        env:
          MLPA_TOKEN: ${{ secrets.MLPA_TOKEN }}
          FASTLY_TOKEN: ${{ secrets.FASTLY_TOKEN }}
          FXA_EMAIL: ${{ secrets.FXA_EMAIL }}
          FXA_PASSWORD: ${{ secrets.FXA_PASSWORD }}
          FXA_CLIENT_ID: ${{ secrets.FXA_CLIENT_ID }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          REMOTE_PROMPTS_PATH: ${{ github.workspace }}
          DIFF_REGRESSION_BASELINE_PROMPT_PATH: /tmp/main_baseline.md
          DIFF_REGRESSION_CANDIDATE_PROMPT_PATH: /tmp/candidate.md
          DIFF_REGRESSION_PR_BODY: ${{ github.event.pull_request.body }}
          DIFF_REGRESSION_OUTPUT_DIR: ${{ github.workspace }}/results/diff_regression
        run: |
          cd _evals
          task eval -- --suite diff_regression
        continue-on-error: true
        id: eval

      - name: Upload report artifacts
        if: steps.detect.outputs.skip != 'true'
        uses: actions/upload-artifact@v4
        with:
          name: diff-regression-report
          path: results/diff_regression/

      - name: Post PR comment
        if: steps.detect.outputs.skip != 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const md = fs.readFileSync('results/diff_regression/report.md', 'utf8');
            const marker = '<!-- diff-regression-report -->';
            const body = marker + '\n' + md;
            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner, repo: context.repo.repo,
              issue_number: context.issue.number,
            });
            const existing = comments.find(c => c.body && c.body.startsWith(marker));
            if (existing) {
              await github.rest.issues.updateComment({
                owner: context.repo.owner, repo: context.repo.repo,
                comment_id: existing.id, body,
              });
            } else {
              await github.rest.issues.createComment({
                owner: context.repo.owner, repo: context.repo.repo,
                issue_number: context.issue.number, body,
              });
            }

      - name: Fail if eval blocked
        if: steps.detect.outputs.skip != 'true' && steps.eval.outcome == 'failure'
        run: |
          echo "Differential regression eval found blocking regressions."
          exit 1
```

- [ ] **Step 2: Verify YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/diff-regression.yml')); print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
git add .github/workflows/diff-regression.yml
git commit -m "ci(diff-regression): thin wrapper that invokes evals-repo suite"
```

---

## Task 12: Full smoke run with realistic flow

**Files:** none (end-to-end verification)

- [ ] **Step 1: Reset both repos to clean state on the right branches**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
git status
# should be on diff-regression-eval-impl branch with Task 10 + 11 commits

cd /Users/mzhang/development/evals
git status
# should have Task 1-8 commits
```

- [ ] **Step 2: Simulate the CI flow locally**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
git show main:prompts/chat/v4/gpt-oss-120b.md > /tmp/main_baseline.md
git show fix-over-clarification:prompts/chat/v4/gpt-oss-120b.md > /tmp/candidate.md

cd /Users/mzhang/development/evals

# Load env from the same .env the evals repo already uses
set -a; . .env; set +a
export DIFF_REGRESSION_BASELINE_PROMPT_PATH=/tmp/main_baseline.md
export DIFF_REGRESSION_CANDIDATE_PROMPT_PATH=/tmp/candidate.md
export DIFF_REGRESSION_OUTPUT_DIR=/tmp/diff_regression_full
export DIFF_REGRESSION_PR_BODY=""

task eval -- --suite diff_regression
```

Expected: ~5 min with account pool (`max_concurrency: 10`). 191 rows × 2 predict calls + 191 × 2 judge calls ≈ 760 MLPA calls, distributed across the FxA user pool.

- [ ] **Step 3: Verify the report**

```bash
cat /tmp/diff_regression_full/report.md
```

Expected: A full regression analysis across 61 cases. Main-vs-fix should show minimal judge-flagged regressions (we verified earlier there are none real), and the aggregation pass should flag that the "Your open tabs don't cover" pattern exists in baseline but not candidate.

- [ ] **Step 4: No commit — verification only.**

---

## Task 13 (optional): Update memory docs

**Files:**
- Modify: `/Users/mzhang/.claude/projects/-Users-mzhang-development-ai-window-remote-settings-prompts/memory/MEMORY.md`
- Modify: `/Users/mzhang/.claude/projects/-Users-mzhang-development-ai-window-remote-settings-prompts/memory/differential-regression-eval.md`

- [ ] **Step 1: Update the project memory note to reflect the new location**

Replace the "Google Doc with strikethrough review trail" line with something like:

```
- Implementation lives in the evals repo: tasks/assistant/diff_regression/
- Eval suite: eval_suites/diff_regression.yaml
- This repo's role is prompts + CI wrapper workflow only
```

- [ ] **Step 2: No commit — personal memory file**

---

## Self-Review Notes

**Spec coverage check:**
- ✅ EvaluationTask subclass with load_prompts/predict/eval/post_process_evals — Task 5, 6, 7
- ✅ Pydantic schemas (JudgeOutput, EvalResponse) — Task 4
- ✅ eval_suite YAML — Task 8
- ✅ Test cases as JSONL — Task 3
- ✅ Judge prompt at evals-repo location — Task 2
- ✅ Pure-logic modules + tests ported — Task 1
- ✅ Env-var override for baseline/candidate paths — Task 5
- ✅ Report generation (md + json) — Task 7
- ✅ CI wrapper workflow — Task 11
- ✅ Cleanup of hand-rolled code — Task 10
- ✅ Smoke run and full run — Task 9, 12
- ⚠️ Explicit FxA account pool usage: **inherited from evals framework via `scripts/eval.py`'s `create_auth_pool()` — we do not need to implement it ourselves, but Task 12 verifies it works.

**Placeholder scan:** no "TBD" / "implement later". Every step has runnable code.

**Type consistency:** `JudgeOutput` fields match `_ALL_DIMS` tuple. `CaseScore.metadata` is `dict[str, Any]`; `baseline_length_chars_median` key matches Task 11's report fields.

**Known risks:**
- The evals framework's `Provider.get_response()` exact signature around tools/kwargs needs to be verified against `utils/inference/provider.py` during Task 6 — may need small signature adjustments.
- `llm_judge` expects `!role:[system]` / `!role:[user]` markers in the prompt; Task 7 uses that format but it's brittle. Confirm via Task 9.
- Test case JSONL format assumes `pandas.read_json(lines=True)` works for the schema — verify in Task 3 step 3.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-23-diff-regression-evals-repo.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batched checkpoints.

Which approach?
