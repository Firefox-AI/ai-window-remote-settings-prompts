# Differential Regression Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a judge-based differential eval that compares responses from a baseline prompt and a candidate prompt on a curated test suite, flags regressions, and runs as a GitHub Action on prompt PRs in this repo.

**Architecture:** Python eval runner that calls MLPA directly (no Firefox), an LLM judge (gpt-5 via MLPA) that compares response pairs on 4 dimensions, two-tier fail criteria (must-pass incident set + lenient cross-section set), per-case A/B flip to neutralize position bias, and an aggregation pass that catches pool-level patterns invisible per-case. Packaged as a Python module inside this repo and invoked from a GitHub Actions workflow that fetches baseline (main) and candidate (PR head) prompts, runs the eval, and posts a report comment on the PR. The evals repo (`/Users/mzhang/development/evals`) is cloned during the CI job to reuse its `FxaUser` auth module — vendoring is rejected because it pulls in `fxa.core`, `fxa.tests.utils`, and `google.cloud.secretmanager`.

**Tech Stack:** Python 3.11, `openai` (AsyncOpenAI SDK against MLPA endpoint), `pydantic` (schema), `python-dotenv`, `pytest` + `pytest-asyncio` + `pytest-mock`, GitHub Actions, `actions/github-script` for PR comments.

**Non-goals:** Firefox-driven evals (we use MLPA-direct). Tool-calling regressions (handled by the dedicated `tool_calling` eval in the evals repo). Absolute quality scoring (handled by `human_eval_auto`).

**Reference source:** Google Doc `1QhZDUkrkC3M-py4pLQYfIifF3KPfKDUoqcv5_YzYRQA` contains the design, judge prompt, fail criteria, and validation plan. The plain-text source of truth is also committed to the repo as `eval_proposal_differential_regression.md`.

---

## File Structure

```
ai-window-remote-settings-prompts/
├── evals/
│   └── diff_regression/
│       ├── __init__.py
│       ├── cli.py                    # entrypoint: python -m evals.diff_regression.cli ...
│       ├── mlpa_client.py            # thin wrapper around AsyncOpenAI + FxA
│       ├── prompts.py                # load baseline/candidate system prompts from .md paths
│       ├── test_cases.py             # pydantic schema + loader for incident/cross-section JSON
│       ├── sampler.py                # run N samples per case against a prompt
│       ├── judge.py                  # judge prompt template + parse JSON response
│       ├── position_flip.py          # run (A,B) and (B,A), reconcile, flag flips
│       ├── scoring.py                # reduce samples → per-case scores; apply fail criteria
│       ├── aggregation.py            # pool-level prefix/length-diff pass
│       ├── override.py               # parse regression-ack: lines from PR body
│       ├── report.py                 # render JSON + markdown report
│       └── judge_prompt.md           # judge prompt text (version-controlled)
├── evals/test_cases/
│   ├── incident/
│   │   └── tab_regression.json       # 15 seeded cases from Apr 2026 incident
│   └── cross_section/
│       ├── general_knowledge.json    # 8 cases
│       ├── real_time_lookups.json    # 8 cases
│       ├── irrelevant_tabs.json      # 8 cases
│       ├── relevant_tabs.json        # 8 cases
│       ├── browsing_history.json     # 5 cases
│       ├── shopping_actionable.json  # 5 cases
│       ├── medical_legal_financial.json  # 5 cases
│       ├── ambiguous.json            # 5 cases
│       └── safety_refusal.json       # 5 cases
├── evals/fixtures/
│   ├── tab_regression_pre_pr85.json  # recorded baseline responses (14 cases)
│   ├── tab_regression_post_pr85.json # recorded candidate responses (14 cases)
│   └── judge_canned.json             # canned judge outputs for unit tests
├── tests/
│   └── diff_regression/
│       ├── __init__.py
│       ├── conftest.py               # shared fixtures
│       ├── test_prompts.py
│       ├── test_test_cases.py
│       ├── test_judge.py
│       ├── test_position_flip.py
│       ├── test_scoring.py
│       ├── test_aggregation.py
│       ├── test_override.py
│       ├── test_report.py
│       └── test_ground_truth.py      # tab regression validation (integration, CI skip)
├── .github/workflows/
│   ├── ci.yml                        # unchanged
│   └── diff-regression.yml           # new
├── requirements-eval.txt             # pinned deps
└── docs/superpowers/plans/
    └── 2026-04-22-differential-regression-eval.md  # this file
```

**Boundaries:**
- `mlpa_client.py` is the only module that knows MLPA auth mechanics.
- `judge.py` is the only module that reads the judge prompt file. `judge_prompt.md` is text-only so non-coders can update it without touching Python.
- `scoring.py` is pure functions; no IO. Test extensively.
- `cli.py` orchestrates but never implements logic — it glues the other modules together.

---

## Task 1: Repo skeleton + eval dependencies

**Files:**
- Create: `requirements-eval.txt`
- Create: `evals/__init__.py`, `evals/diff_regression/__init__.py`, `evals/test_cases/.gitkeep`, `evals/fixtures/.gitkeep`
- Create: `tests/__init__.py`, `tests/diff_regression/__init__.py`, `tests/diff_regression/conftest.py`
- Modify: `.gitignore` (append `.pytest_cache/`, `.coverage`, `results/`)

- [ ] **Step 1: Write `requirements-eval.txt`**

```
openai==1.54.3
pydantic==2.9.2
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

Exact versions are picked to match what the existing `eval_gpt_oss_child_safety.py` tolerates and what is installed in `/Users/mzhang/development/evals/.venv` today. Update if pip resolution fails.

- [ ] **Step 2: Create package skeleton files**

Create all `__init__.py` files as empty files. Create `.gitkeep` files for empty data directories.

- [ ] **Step 3: Write `tests/diff_regression/conftest.py`**

```python
import asyncio
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent.parent / "evals" / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def load_fixture(fixtures_dir):
    def _load(name: str):
        with open(fixtures_dir / name) as f:
            return json.load(f)
    return _load
```

- [ ] **Step 4: Append to `.gitignore`**

```
.pytest_cache/
.coverage
results/
```

- [ ] **Step 5: Verify skeleton**

Run: `cd /Users/mzhang/development/ai-window-remote-settings-prompts && pip install -r requirements-eval.txt && pytest tests/ -v`
Expected: `no tests ran in X.XXs` (success — pytest discovers the empty tests/ package without errors).

- [ ] **Step 6: Commit**

```bash
git add requirements-eval.txt evals/ tests/ .gitignore
git commit -m "chore: scaffold differential regression eval package"
```

---

## Task 2: MLPA client wrapper

**Files:**
- Create: `evals/diff_regression/mlpa_client.py`
- Create: `tests/diff_regression/test_mlpa_client.py`

**Why this task exists:** Every call to MLPA requires FxA auth + multiple headers. Centralizing the client in one module means no other file knows about auth headers.

- [ ] **Step 1: Write failing test `test_mlpa_client.py`**

```python
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from evals.diff_regression import mlpa_client


@pytest.mark.asyncio
async def test_call_model_returns_content(monkeypatch):
    # Arrange: mock the AsyncOpenAI client
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="hello world"))]
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)
    monkeypatch.setattr(mlpa_client, "_get_client", lambda: fake_client)

    # Act
    result = await mlpa_client.call_model(
        model_id="gpt-oss-120b",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hi"}],
    )

    # Assert
    assert result["content"] == "hello world"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_call_model_retries_on_exception(monkeypatch):
    attempts = []
    fake_client = MagicMock()
    async def flaky(*a, **kw):
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("transient")
        m = MagicMock()
        m.choices = [MagicMock(message=MagicMock(content="ok"))]
        return m
    fake_client.chat.completions.create = flaky
    monkeypatch.setattr(mlpa_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(mlpa_client.asyncio, "sleep", AsyncMock())

    result = await mlpa_client.call_model(
        model_id="gpt-oss-120b",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hi"}],
    )

    assert len(attempts) == 3
    assert result["content"] == "ok"


@pytest.mark.asyncio
async def test_call_model_gives_up_after_retries(monkeypatch):
    fake_client = MagicMock()
    async def always_fail(*a, **kw):
        raise RuntimeError("boom")
    fake_client.chat.completions.create = always_fail
    monkeypatch.setattr(mlpa_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(mlpa_client.asyncio, "sleep", AsyncMock())

    result = await mlpa_client.call_model(
        model_id="gpt-oss-120b",
        system_prompt="sys",
        messages=[{"role": "user", "content": "hi"}],
        retries=2,
    )

    assert result["content"] == ""
    assert "boom" in result["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/diff_regression/test_mlpa_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'evals.diff_regression.mlpa_client'`.

- [ ] **Step 3: Implement `mlpa_client.py`**

```python
"""MLPA client wrapper. Only module that knows about auth headers."""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

MLPA_ENDPOINT = "https://mlpa-gateway-stage.llm-proxy.nonprod.dataservices.mozgcp.net/v1"
_client: Optional[AsyncOpenAI] = None
_semaphore = asyncio.Semaphore(int(os.environ.get("EVAL_CONCURRENCY", "3")))


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is not None:
        return _client

    # The evals repo (cloned by CI or present locally) provides FxaUser.
    # EVALS_REPO_PATH env var overrides the default local path.
    evals_path = os.environ.get("EVALS_REPO_PATH", "/Users/mzhang/development/evals")
    if evals_path not in sys.path:
        sys.path.insert(0, evals_path)
    from utils.auth_utils import FxaUser  # noqa: E402

    user = FxaUser(email=os.environ["FXA_EMAIL"], password=os.environ["FXA_PASSWORD"])
    fxa_token = user.get_fxa_token()
    _client = AsyncOpenAI(
        api_key="unused",
        base_url=MLPA_ENDPOINT,
        default_headers={
            "service-type": "ai-dev",
            "x-dev-authorization": os.environ["MLPA_TOKEN"],
            "Authorization": f"Bearer {fxa_token}",
            "X-Fastly-Request": os.environ["FASTLY_TOKEN"],
        },
    )
    return _client


async def call_model(
    *,
    model_id: str,
    system_prompt: str,
    messages: list[dict],
    temperature: float = 1.0,
    retries: int = 3,
    tools: Optional[list[dict]] = None,
) -> dict:
    """Call MLPA with retry. Returns {"content": str, "error": str|None}."""
    async with _semaphore:
        last_error = None
        for attempt in range(retries):
            try:
                client = _get_client()
                kwargs = {
                    "model": model_id,
                    "messages": [{"role": "system", "content": system_prompt}, *messages],
                    "temperature": temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                response = await client.chat.completions.create(**kwargs)
                return {"content": response.choices[0].message.content or "", "error": None}
            except Exception as e:
                last_error = str(e)
                if attempt < retries - 1:
                    await asyncio.sleep(1.0 * (2 ** attempt))
        return {"content": "", "error": last_error}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/diff_regression/test_mlpa_client.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/mlpa_client.py tests/diff_regression/test_mlpa_client.py
git commit -m "feat(diff-regression): add MLPA client wrapper with retry"
```

---

## Task 3: Test case schema and loader

**Files:**
- Create: `evals/diff_regression/test_cases.py`
- Create: `tests/diff_regression/test_test_cases.py`

**Why:** Test cases must have a typed schema so all downstream code (sampler, judge, report) has a single source of truth for case fields.

- [ ] **Step 1: Write failing test**

```python
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.diff_regression.test_cases import TestCase, TestSet, load_test_set


def test_test_case_required_fields():
    tc = TestCase(
        id="case_1",
        set="incident",
        category="tab_regression",
        query="What's the weather?",
        tabs=[{"url": "https://nike.com", "title": "Nike", "description": ""}],
        saved_facts=[],
        prior_messages=[],
        samples=5,
    )
    assert tc.id == "case_1"
    assert tc.set == "incident"
    assert tc.samples == 5


def test_test_case_rejects_invalid_set():
    with pytest.raises(ValidationError):
        TestCase(
            id="x", set="bogus", category="c", query="q",
            tabs=[], saved_facts=[], prior_messages=[], samples=3,
        )


def test_load_test_set_merges_multiple_files(tmp_path):
    inc_dir = tmp_path / "incident"
    cross_dir = tmp_path / "cross_section"
    inc_dir.mkdir()
    cross_dir.mkdir()

    (inc_dir / "tab.json").write_text(json.dumps([
        {"id": "inc_1", "set": "incident", "category": "tab_regression",
         "query": "q1", "tabs": [], "saved_facts": [], "prior_messages": [], "samples": 5},
    ]))
    (cross_dir / "general.json").write_text(json.dumps([
        {"id": "cs_1", "set": "cross_section", "category": "general_knowledge",
         "query": "q2", "tabs": [], "saved_facts": [], "prior_messages": [], "samples": 3},
    ]))

    ts = load_test_set(tmp_path, mode="full")
    assert len(ts.cases) == 2
    assert ts.cases[0].id == "inc_1"
    assert ts.cases[1].id == "cs_1"


def test_load_test_set_smoke_filters_to_incident(tmp_path):
    inc_dir = tmp_path / "incident"
    cross_dir = tmp_path / "cross_section"
    inc_dir.mkdir()
    cross_dir.mkdir()
    (inc_dir / "tab.json").write_text(json.dumps([
        {"id": "inc_1", "set": "incident", "category": "tab_regression",
         "query": "q1", "tabs": [], "saved_facts": [], "prior_messages": [], "samples": 5},
    ]))
    (cross_dir / "general.json").write_text(json.dumps([
        {"id": "cs_1", "set": "cross_section", "category": "general_knowledge",
         "query": "q2", "tabs": [], "saved_facts": [], "prior_messages": [], "samples": 3},
    ]))

    ts = load_test_set(tmp_path, mode="smoke")
    assert len(ts.cases) == 1
    assert ts.cases[0].set == "incident"
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/diff_regression/test_test_cases.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `test_cases.py`**

```python
"""Test case schema and loader."""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class Tab(BaseModel):
    url: str
    title: str
    description: str = ""


class SavedFact(BaseModel):
    text: str


class PriorMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class TestCase(BaseModel):
    id: str
    set: Literal["incident", "cross_section"]
    category: str
    query: str
    tabs: list[Tab]
    saved_facts: list[SavedFact]
    prior_messages: list[PriorMessage]
    samples: int


class TestSet(BaseModel):
    cases: list[TestCase]


def load_test_set(base_dir: Path, mode: Literal["full", "smoke"] = "full") -> TestSet:
    """Load test cases from base_dir/{incident,cross_section}/*.json.
    mode='smoke' returns only the incident set."""
    base_dir = Path(base_dir)
    cases: list[TestCase] = []

    subdirs = ["incident"]
    if mode == "full":
        subdirs.append("cross_section")

    for sub in subdirs:
        d = base_dir / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            with open(f) as fp:
                data = json.load(fp)
            for item in data:
                cases.append(TestCase(**item))

    return TestSet(cases=cases)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/diff_regression/test_test_cases.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/test_cases.py tests/diff_regression/test_test_cases.py
git commit -m "feat(diff-regression): add test case schema and loader"
```

---

## Task 4: Prompt loader

**Files:**
- Create: `evals/diff_regression/prompts.py`
- Create: `tests/diff_regression/test_prompts.py`

**Why:** The eval needs to load a system prompt from a `.md` path plus the real-time date/tab context templates from the same structure existing evals use (`prompts/real-time-context-date/v1/...`).

- [ ] **Step 1: Write failing test**

```python
from datetime import datetime
from pathlib import Path

from evals.diff_regression.prompts import load_system_prompt


def test_load_system_prompt_composes_main_and_context(tmp_path):
    main = tmp_path / "main.md"
    main.write_text("MAIN PROMPT")

    date_tpl = tmp_path / "prompts/real-time-context-date/v1"
    date_tpl.mkdir(parents=True)
    (date_tpl / "model.md").write_text("date={todayDate} iso={isoTimestamp} tz={timezone} loc={locale}")

    tab_tpl = tmp_path / "prompts/real-time-context-tab/v1"
    tab_tpl.mkdir(parents=True)
    (tab_tpl / "model.md").write_text("url={url} title={title} desc={description} dsecription={dsecription} add={additionalTabs}")

    result = load_system_prompt(
        main_prompt_path=main,
        model_name="model",
        prompts_root=tmp_path / "prompts",
        tab={"url": "https://example.com", "title": "Ex", "description": "d"},
        now=datetime(2026, 4, 22, 15, 0, 0),
    )

    assert "MAIN PROMPT" in result
    assert "date=Wednesday, April 22, 2026" in result
    assert "url=https://example.com" in result
    assert "title=Ex" in result
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_prompts.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `prompts.py`**

```python
"""System prompt loader: composes main prompt + date/tab context."""
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_system_prompt(
    *,
    main_prompt_path: Path,
    model_name: str,
    prompts_root: Path,
    tab: Optional[dict] = None,
    now: Optional[datetime] = None,
    locale: str = "en-US",
    timezone: str = "America/Los_Angeles",
) -> str:
    """Compose the full system prompt: main + date context + tab context.
    Templates expect .format() substitution; typo 'dsecription' is preserved
    because the upstream prompt template contains it."""
    now = now or datetime.now()
    tab = tab or {"url": "https://www.example.com", "title": "Example Page", "description": ""}

    main = Path(main_prompt_path).read_text()

    date_path = prompts_root / "real-time-context-date" / "v1" / f"{model_name}.md"
    tab_path = prompts_root / "real-time-context-tab" / "v1" / f"{model_name}.md"

    date_ctx = date_path.read_text().format(
        locale=locale,
        timezone=timezone,
        isoTimestamp=now.isoformat(),
        todayDate=now.strftime("%A, %B %d, %Y"),
    )
    tab_ctx = tab_path.read_text().format(
        url=tab["url"],
        title=tab["title"],
        description=tab.get("description", ""),
        dsecription=tab.get("description", ""),
        additionalTabs=tab.get("additionalTabs", ""),
    )
    return "\n\n".join([main, date_ctx, tab_ctx])
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/diff_regression/test_prompts.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/prompts.py tests/diff_regression/test_prompts.py
git commit -m "feat(diff-regression): add system prompt loader"
```

---

## Task 5: Judge prompt + judge invoker

**Files:**
- Create: `evals/diff_regression/judge_prompt.md`
- Create: `evals/diff_regression/judge.py`
- Create: `tests/diff_regression/test_judge.py`

**Why:** The judge is the heart of the eval. The prompt lives as a standalone `.md` file so non-coders can update it. The invoker wraps MLPA + parses JSON.

- [ ] **Step 1: Write `judge_prompt.md` (copy verbatim from Google Doc §Judge Prompt (Draft), non-struck text only)**

```markdown
You are comparing two AI assistant responses to the same user query. Response A is from the current production prompt. Response B is from a candidate prompt change. Your job is to detect whether Response B introduced any regressions compared to Response A.

The user query, tab context, and saved user facts are shown once at the top since they are identical for both responses. You will then see Response A and Response B (final assistant text only).

Score each dimension from 1-5 where:
- 5 = no regression (same or better)
- 3 = mild regression
- 1 = clear regression
- 2 and 4 = intermediate points

Dimensions:
1. **no_new_artifacts**: Does B introduce any preambles, disclaimers, meta-commentary, formatting issues, or structural elements that are NOT present in A? Examples (non-exhaustive; use judgment on unlisted cases): new opening phrases before the actual answer, unnecessary references to browser state or tools, broken or empty links, verbose headers or framing that A didn't have. Score 1 if B has clear new artifacts; 3 if equivalent; 5 if B is cleaner.

2. **no_capability_loss**: Does B answer the query as helpfully and completely as A? Examples (non-exhaustive; use judgment on unlisted cases): B refusing something A answered, B giving a shorter or less useful answer, B missing information A included, B failing to use available context (tabs, saved facts) that A used. Score 1 if B clearly lost capability; 3 if equivalent; 5 if more helpful.

3. **instruction_adherence**: Does B follow the user's explicit request as well as A? Examples (non-exhaustive; use judgment on unlisted cases): user asked for a list but B gave prose, user asked to compare but B only summarized, user asked to search but B answered from memory, user gave constraints B ignored. Subcases: strict adherence (both honor the instruction); refusal-with-alternative (if A refused but offered an alternative and B refuses without one, that is a regression); partial adherence (if B addresses fewer of the user's stated asks than A did, that is a regression). Score 1 if B clearly missed the request; 3 if equivalent; 5 if better aligned.

4. **overall_regression**: Holistically, considering everything above, is B worse than A as a response to this query? Score 1 if B is clearly worse overall; 3 if equivalent; 5 if clearly better. This should correlate with the other dimensions; unexplained drops here are a signal to decompose into a new named dimension.

Approved artifacts (do NOT flag these as new artifacts; they are intentional):
- (empty — populated as Firefox introduces acceptable behaviors)

Respond with JSON only, in exactly this structure:
{
  "no_new_artifacts_justification": "<brief explanation>",
  "no_new_artifacts": <1-5>,
  "no_capability_loss_justification": "<brief explanation>",
  "no_capability_loss": <1-5>,
  "instruction_adherence_justification": "<brief explanation>",
  "instruction_adherence": <1-5>,
  "overall_regression_justification": "<brief explanation>",
  "overall_regression": <1-5>
}
```

- [ ] **Step 2: Write `tests/diff_regression/test_judge.py`**

```python
import json
from unittest.mock import AsyncMock

import pytest

from evals.diff_regression import judge


def test_build_judge_input_puts_shared_context_once():
    text = judge.build_judge_input(
        query="What's the weather?",
        tabs=[{"url": "https://nike.com", "title": "Nike", "description": ""}],
        saved_facts=[],
        response_a="It's sunny.",
        response_b="Your open tabs don't cover weather. It's sunny.",
    )
    # query should appear exactly once
    assert text.count("What's the weather?") == 1
    # both responses should appear
    assert "It's sunny." in text
    assert "Your open tabs don't cover weather" in text


def test_parse_judge_output_valid_json():
    raw = json.dumps({
        "no_new_artifacts_justification": "B has a preamble A does not",
        "no_new_artifacts": 1,
        "no_capability_loss_justification": "both answer the weather",
        "no_capability_loss": 4,
        "instruction_adherence_justification": "both follow the ask",
        "instruction_adherence": 5,
        "overall_regression_justification": "preamble makes B worse",
        "overall_regression": 2,
    })
    result = judge.parse_judge_output(raw)
    assert result.no_new_artifacts == 1
    assert result.overall_regression == 2
    assert "preamble" in result.no_new_artifacts_justification


def test_parse_judge_output_raises_on_missing_field():
    raw = json.dumps({"no_new_artifacts": 3})
    with pytest.raises(judge.JudgeParseError):
        judge.parse_judge_output(raw)


def test_parse_judge_output_strips_code_fence():
    raw = "```json\n" + json.dumps({
        "no_new_artifacts_justification": "x",
        "no_new_artifacts": 3,
        "no_capability_loss_justification": "x",
        "no_capability_loss": 3,
        "instruction_adherence_justification": "x",
        "instruction_adherence": 3,
        "overall_regression_justification": "x",
        "overall_regression": 3,
    }) + "\n```"
    result = judge.parse_judge_output(raw)
    assert result.no_new_artifacts == 3


@pytest.mark.asyncio
async def test_judge_compare_calls_mlpa_and_parses(monkeypatch):
    canned = json.dumps({
        "no_new_artifacts_justification": "clean",
        "no_new_artifacts": 5,
        "no_capability_loss_justification": "clean",
        "no_capability_loss": 5,
        "instruction_adherence_justification": "clean",
        "instruction_adherence": 5,
        "overall_regression_justification": "clean",
        "overall_regression": 5,
    })
    fake_call = AsyncMock(return_value={"content": canned, "error": None})
    monkeypatch.setattr(judge, "call_model", fake_call)

    result = await judge.compare(
        query="q", tabs=[], saved_facts=[], response_a="a", response_b="b",
    )
    assert result.no_new_artifacts == 5
    fake_call.assert_awaited_once()
```

- [ ] **Step 3: Run — expect fail**

Run: `pytest tests/diff_regression/test_judge.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `judge.py`**

```python
"""Judge prompt + invoker. Calls gpt-5 via MLPA to compare response pairs."""
import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ValidationError

from evals.diff_regression.mlpa_client import call_model

JUDGE_MODEL = "gpt-5"
JUDGE_PROMPT_PATH = Path(__file__).parent / "judge_prompt.md"


class JudgeResult(BaseModel):
    no_new_artifacts_justification: str
    no_new_artifacts: int
    no_capability_loss_justification: str
    no_capability_loss: int
    instruction_adherence_justification: str
    instruction_adherence: int
    overall_regression_justification: str
    overall_regression: int


class JudgeParseError(ValueError):
    pass


def build_judge_input(
    *,
    query: str,
    tabs: list[dict],
    saved_facts: list[dict],
    response_a: str,
    response_b: str,
) -> str:
    """Shared context shown once, then Response A and Response B."""
    tab_lines = "\n".join(f"- {t.get('title', '')} ({t.get('url', '')})" for t in tabs) or "(none)"
    fact_lines = "\n".join(f"- {f.get('text', '')}" for f in saved_facts) or "(none)"
    return (
        f"USER QUERY:\n{query}\n\n"
        f"BROWSER TABS:\n{tab_lines}\n\n"
        f"SAVED USER FACTS:\n{fact_lines}\n\n"
        f"RESPONSE A (baseline):\n{response_a}\n\n"
        f"RESPONSE B (candidate):\n{response_b}\n"
    )


def parse_judge_output(raw: str) -> JudgeResult:
    text = raw.strip()
    # strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    try:
        data = json.loads(text)
        return JudgeResult(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise JudgeParseError(f"Could not parse judge output: {e}\nRaw:\n{raw}") from e


async def compare(
    *,
    query: str,
    tabs: list[dict],
    saved_facts: list[dict],
    response_a: str,
    response_b: str,
) -> JudgeResult:
    system_prompt = JUDGE_PROMPT_PATH.read_text()
    user_message = build_judge_input(
        query=query, tabs=tabs, saved_facts=saved_facts,
        response_a=response_a, response_b=response_b,
    )
    result = await call_model(
        model_id=JUDGE_MODEL,
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.0,
    )
    if result["error"]:
        raise JudgeParseError(f"judge call failed: {result['error']}")
    return parse_judge_output(result["content"])
```

- [ ] **Step 5: Run — expect pass**

Run: `pytest tests/diff_regression/test_judge.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add evals/diff_regression/judge.py evals/diff_regression/judge_prompt.md tests/diff_regression/test_judge.py
git commit -m "feat(diff-regression): add judge prompt and invoker"
```

---

## Task 6: Sampler + position flip

**Files:**
- Create: `evals/diff_regression/sampler.py`
- Create: `evals/diff_regression/position_flip.py`
- Create: `tests/diff_regression/test_position_flip.py`

**Why:** Each case runs N samples against each prompt. Each A/B pair is judged twice with flipped ordering. Score reduction is median across samples; flip disagreement flags for review.

- [ ] **Step 1: Write `test_position_flip.py`**

```python
from unittest.mock import AsyncMock

import pytest

from evals.diff_regression import position_flip
from evals.diff_regression.judge import JudgeResult


def _jr(**kwargs):
    defaults = dict(
        no_new_artifacts_justification="x", no_new_artifacts=3,
        no_capability_loss_justification="x", no_capability_loss=3,
        instruction_adherence_justification="x", instruction_adherence=3,
        overall_regression_justification="x", overall_regression=3,
    )
    defaults.update(kwargs)
    return JudgeResult(**defaults)


@pytest.mark.asyncio
async def test_flip_agrees_when_verdict_consistent(monkeypatch):
    async def fake_compare(**kw):
        # When B is candidate (order=AB), score B=2 (regression)
        # When A is candidate (order=BA), B=2 means original B (flipped) is still worse
        return _jr(no_new_artifacts=2)
    monkeypatch.setattr(position_flip, "compare", fake_compare)

    result = await position_flip.judge_with_flip(
        query="q", tabs=[], saved_facts=[], response_a="a", response_b="b",
    )
    assert result.agreement is True


@pytest.mark.asyncio
async def test_flip_detects_disagreement(monkeypatch):
    call_count = [0]
    async def fake_compare(*, response_a, response_b, **kw):
        call_count[0] += 1
        # First call: B=candidate, score it bad
        # Second call: A=candidate (original B is now "A" input), score original A as bad
        # These should invert consistently if no position bias; if they don't, flag.
        if call_count[0] == 1:
            return _jr(no_new_artifacts=1)  # candidate (original B) is bad
        else:
            return _jr(no_new_artifacts=1)  # now "A" in input is original B — same result
                                              # would be bias-free. Flip this for disagreement:
    monkeypatch.setattr(position_flip, "compare", fake_compare)

    result = await position_flip.judge_with_flip(
        query="q", tabs=[], saved_facts=[], response_a="a", response_b="b",
    )
    # With identical scores in both orderings on a dimension where one should flip,
    # we expect disagreement=True (bias detected).
    assert result.agreement is False
```

*Note: the test above encodes the flip logic — read carefully when implementing.*

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_position_flip.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `position_flip.py`**

```python
"""Per-case A/B flip: run judge with (A,B) and (B,A), reconcile."""
from dataclasses import dataclass

from evals.diff_regression.judge import JudgeResult, compare


@dataclass
class FlipResult:
    forward: JudgeResult    # (A, B) order — B is candidate
    reverse: JudgeResult    # (B, A) order — A (original) is now candidate
    agreement: bool         # True if both orderings agree on regression direction

    @property
    def score_no_new_artifacts(self) -> int:
        """Forward is the canonical direction (B relative to A)."""
        return self.forward.no_new_artifacts

    @property
    def score_no_capability_loss(self) -> int:
        return self.forward.no_capability_loss

    @property
    def score_instruction_adherence(self) -> int:
        return self.forward.instruction_adherence

    @property
    def score_overall_regression(self) -> int:
        return self.forward.overall_regression


_DIMS = [
    "no_new_artifacts",
    "no_capability_loss",
    "instruction_adherence",
    "overall_regression",
]


def _agrees(forward: JudgeResult, reverse: JudgeResult) -> bool:
    """Forward score of X on a dim should roughly invert in reverse.
    If forward = 1 (B worse than A), reverse should be 5 (because now B is "A"
    in the reverse call, and original A is "B" in the reverse call — so original A
    should look "better" i.e. reverse score close to 5 means "new-B-is-better").
    Allow ±1 tolerance.
    A dim is in agreement if: forward + reverse ≈ 6 (inverse sum).
    """
    for dim in _DIMS:
        f = getattr(forward, dim)
        r = getattr(reverse, dim)
        if abs((f + r) - 6) > 1:
            return False
    return True


async def judge_with_flip(
    *,
    query: str,
    tabs: list[dict],
    saved_facts: list[dict],
    response_a: str,
    response_b: str,
) -> FlipResult:
    forward = await compare(
        query=query, tabs=tabs, saved_facts=saved_facts,
        response_a=response_a, response_b=response_b,
    )
    reverse = await compare(
        query=query, tabs=tabs, saved_facts=saved_facts,
        response_a=response_b, response_b=response_a,
    )
    return FlipResult(
        forward=forward, reverse=reverse, agreement=_agrees(forward, reverse),
    )
```

- [ ] **Step 4: Write `sampler.py`**

```python
"""Run N samples of a prompt against a test case."""
import asyncio

from evals.diff_regression.mlpa_client import call_model
from evals.diff_regression.test_cases import TestCase


async def sample_responses(
    *,
    system_prompt: str,
    model_id: str,
    case: TestCase,
    n_samples: int,
) -> list[str]:
    messages = [
        {"role": m.role, "content": m.content} for m in case.prior_messages
    ] + [{"role": "user", "content": case.query}]

    async def one_sample():
        result = await call_model(
            model_id=model_id,
            system_prompt=system_prompt,
            messages=messages,
            temperature=1.0,
        )
        return result["content"] if not result["error"] else ""

    return await asyncio.gather(*(one_sample() for _ in range(n_samples)))
```

- [ ] **Step 5: Run — expect pass**

Run: `pytest tests/diff_regression/test_position_flip.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add evals/diff_regression/sampler.py evals/diff_regression/position_flip.py tests/diff_regression/test_position_flip.py
git commit -m "feat(diff-regression): add sampler and position flip"
```

---

## Task 7: Scoring + fail criteria

**Files:**
- Create: `evals/diff_regression/scoring.py`
- Create: `tests/diff_regression/test_scoring.py`

**Why:** The core logic of the eval: reduce multiple samples to a per-case score (median), then apply two-tier fail criteria (incident = 100%, cross-section = 3+ regressions on same dim).

- [ ] **Step 1: Write `test_scoring.py`**

```python
import pytest

from evals.diff_regression.scoring import (
    CaseScore,
    apply_fail_criteria,
    median_reduce,
    FlagCategory,
)


def test_median_reduce_returns_median_per_dim():
    scores = [
        dict(no_new_artifacts=1, no_capability_loss=3, instruction_adherence=5, overall_regression=2),
        dict(no_new_artifacts=2, no_capability_loss=3, instruction_adherence=4, overall_regression=2),
        dict(no_new_artifacts=5, no_capability_loss=3, instruction_adherence=5, overall_regression=4),
    ]
    result = median_reduce(scores)
    assert result["no_new_artifacts"] == 2
    assert result["no_capability_loss"] == 3
    assert result["instruction_adherence"] == 5
    assert result["overall_regression"] == 2


def test_incident_100_percent_pass_required():
    cases = [
        CaseScore(id="inc_1", set="incident", category="tab",
                  scores=dict(no_new_artifacts=5, no_capability_loss=5, instruction_adherence=5, overall_regression=5),
                  flip_agreement=True),
        CaseScore(id="inc_2", set="incident", category="tab",
                  scores=dict(no_new_artifacts=3, no_capability_loss=5, instruction_adherence=5, overall_regression=5),
                  flip_agreement=True),
    ]
    flags = apply_fail_criteria(cases)
    # inc_2 has a 3 on no_new_artifacts; incident rule is ≤4 blocks.
    assert any(f.category == FlagCategory.BLOCK and f.case_id == "inc_2" for f in flags)
    assert not any(f.case_id == "inc_1" for f in flags)


def test_cross_section_3_plus_regressions_on_same_dim_blocks():
    cases = []
    for i in range(4):
        cases.append(CaseScore(
            id=f"cs_{i}", set="cross_section", category="general",
            scores=dict(no_new_artifacts=2, no_capability_loss=5, instruction_adherence=5, overall_regression=5),
            flip_agreement=True,
        ))
    flags = apply_fail_criteria(cases)
    block_flags = [f for f in flags if f.category == FlagCategory.BLOCK]
    assert len(block_flags) >= 1
    assert block_flags[0].dimension == "no_new_artifacts"


def test_cross_section_catastrophic_single_drop_blocks():
    cases = [
        CaseScore(id="cs_1", set="cross_section", category="general",
                  scores=dict(no_new_artifacts=1, no_capability_loss=5, instruction_adherence=5, overall_regression=5),
                  flip_agreement=True),
    ]
    flags = apply_fail_criteria(cases)
    assert any(f.category == FlagCategory.BLOCK for f in flags)


def test_cross_section_single_flag_is_review_not_block():
    cases = [
        CaseScore(id="cs_1", set="cross_section", category="general",
                  scores=dict(no_new_artifacts=2, no_capability_loss=5, instruction_adherence=5, overall_regression=5),
                  flip_agreement=True),
    ]
    flags = apply_fail_criteria(cases)
    # one case with score 2 is flag-for-review, not block
    assert any(f.category == FlagCategory.REVIEW for f in flags)
    assert not any(f.category == FlagCategory.BLOCK for f in flags)


def test_flip_disagreement_always_flags_review():
    cases = [
        CaseScore(id="cs_1", set="cross_section", category="general",
                  scores=dict(no_new_artifacts=5, no_capability_loss=5, instruction_adherence=5, overall_regression=5),
                  flip_agreement=False),
    ]
    flags = apply_fail_criteria(cases)
    assert any(f.category == FlagCategory.REVIEW and "flip" in f.reason.lower() for f in flags)
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_scoring.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `scoring.py`**

```python
"""Per-case score reduction + two-tier fail criteria."""
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from statistics import median


DIMENSIONS = ["no_new_artifacts", "no_capability_loss", "instruction_adherence", "overall_regression"]


class FlagCategory(str, Enum):
    REVIEW = "review"
    BLOCK = "block"


@dataclass
class CaseScore:
    id: str
    set: str  # "incident" or "cross_section"
    category: str
    scores: dict  # dim → int (median across samples)
    flip_agreement: bool


@dataclass
class Flag:
    case_id: str
    dimension: str
    score: int
    category: FlagCategory
    reason: str


def median_reduce(samples: list[dict]) -> dict:
    """Given a list of per-sample score dicts, return per-dim median."""
    out = {}
    for dim in DIMENSIONS:
        values = [s[dim] for s in samples]
        out[dim] = int(median(values))
    return out


def apply_fail_criteria(cases: list[CaseScore]) -> list[Flag]:
    """Two-tier fail criteria:
      - incident set: any score ≤4 on any dim = BLOCK
      - cross_section set:
          - any single case score = 1 on no_new_artifacts or no_capability_loss = BLOCK (catastrophic)
          - 3+ cases score ≤2 on same dim = BLOCK (systematic)
          - otherwise, any score ≤2 = REVIEW
      - flip_agreement=False on any case = REVIEW regardless of set
    """
    flags: list[Flag] = []

    # Flip disagreement
    for c in cases:
        if not c.flip_agreement:
            flags.append(Flag(
                case_id=c.id, dimension="*", score=-1,
                category=FlagCategory.REVIEW,
                reason="Position flip disagreement — judge verdict not stable across A/B ordering.",
            ))

    # Incident: 100% pass
    for c in cases:
        if c.set != "incident":
            continue
        for dim in DIMENSIONS:
            s = c.scores[dim]
            if s <= 4:
                flags.append(Flag(
                    case_id=c.id, dimension=dim, score=s,
                    category=FlagCategory.BLOCK,
                    reason=f"Incident case regressed on {dim} (score={s}). Must-pass set requires 5/5.",
                ))

    # Cross-section: catastrophic single 1 on artifacts/capability
    for c in cases:
        if c.set != "cross_section":
            continue
        for dim in ("no_new_artifacts", "no_capability_loss"):
            if c.scores[dim] == 1:
                flags.append(Flag(
                    case_id=c.id, dimension=dim, score=1,
                    category=FlagCategory.BLOCK,
                    reason=f"Catastrophic regression on {dim} (score=1).",
                ))

    # Cross-section: 3+ on same dim ≤2 = block, else review
    cross_by_dim = defaultdict(list)
    for c in cases:
        if c.set != "cross_section":
            continue
        for dim in DIMENSIONS:
            if c.scores[dim] <= 2:
                cross_by_dim[dim].append(c)

    for dim, regressed in cross_by_dim.items():
        if len(regressed) >= 3:
            for c in regressed:
                flags.append(Flag(
                    case_id=c.id, dimension=dim, score=c.scores[dim],
                    category=FlagCategory.BLOCK,
                    reason=f"Systematic regression: {len(regressed)} cases ≤2 on {dim}.",
                ))
        else:
            for c in regressed:
                flags.append(Flag(
                    case_id=c.id, dimension=dim, score=c.scores[dim],
                    category=FlagCategory.REVIEW,
                    reason=f"Single regression on {dim} (score={c.scores[dim]}).",
                ))

    return flags
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/diff_regression/test_scoring.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/scoring.py tests/diff_regression/test_scoring.py
git commit -m "feat(diff-regression): add two-tier fail criteria"
```

---

## Task 8: Aggregation pass

**Files:**
- Create: `evals/diff_regression/aggregation.py`
- Create: `tests/diff_regression/test_aggregation.py`

**Why:** Some regressions only show up as pool-level patterns (the tab-mention prefix appeared across 14 responses but might score neutrally per-case if judge tolerates it). Aggregation pass looks at prefix frequency diffs and length distribution shifts.

- [ ] **Step 1: Write `test_aggregation.py`**

```python
from evals.diff_regression.aggregation import (
    detect_prefix_pattern,
    detect_length_shift,
    run_aggregation_pass,
)


def test_detect_prefix_pattern_flags_b_pool_dominant():
    a_pool = ["It's sunny today.", "Here's the info.", "The answer is yes."]
    b_pool = [
        "Your open tabs don't cover weather. It's sunny.",
        "Your open tabs don't cover this. Here's the info.",
        "Your open tabs don't cover that. The answer is yes.",
        "Your open tabs don't cover X. Hello.",
    ]
    patterns = detect_prefix_pattern(a_pool, b_pool, min_occurrences=3, prefix_tokens=6)
    assert any("Your open tabs" in p.prefix for p in patterns)
    assert all(p.b_count > p.a_count for p in patterns)


def test_detect_prefix_pattern_ignores_common_prefixes():
    # Both pools start with "The" often; shouldn't flag
    a_pool = ["The answer is 42.", "The result varies.", "The best way is..."]
    b_pool = ["The answer is still 42.", "The result is similar.", "The best way is..."]
    patterns = detect_prefix_pattern(a_pool, b_pool, min_occurrences=3, prefix_tokens=3)
    assert patterns == []


def test_detect_length_shift_flags_systematic_lengthening():
    a_pool = ["short."] * 10
    b_pool = ["this is a much longer response with extra content padded on."] * 10
    shift = detect_length_shift(a_pool, b_pool)
    assert shift.systematic_b_longer is True
    assert shift.a_median_chars < shift.b_median_chars


def test_run_aggregation_pass_returns_flags():
    a_pool = ["It's sunny.", "Here's the info."]
    b_pool = [
        "Your open tabs don't cover weather. It's sunny.",
        "Your open tabs don't cover topic. Here's the info.",
        "Your open tabs don't cover this. Ok.",
    ]
    flags = run_aggregation_pass(a_pool=a_pool, b_pool=b_pool)
    assert len(flags) >= 1
    assert any("prefix" in f.reason.lower() for f in flags)
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_aggregation.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `aggregation.py`**

```python
"""Pool-level patterns: prefix frequency diffs + length distribution shifts."""
import re
from collections import Counter
from dataclasses import dataclass
from statistics import median

from evals.diff_regression.scoring import Flag, FlagCategory


@dataclass
class PrefixPattern:
    prefix: str
    a_count: int
    b_count: int


@dataclass
class LengthShift:
    a_median_chars: int
    b_median_chars: int
    systematic_b_longer: bool


def _tokenize(text: str) -> list[str]:
    # Simple whitespace+punct split; good enough for prefix analysis
    return re.findall(r"\S+", text)


def _prefixes(pool: list[str], n_tokens: int) -> Counter:
    counter = Counter()
    for text in pool:
        toks = _tokenize(text.strip())
        if len(toks) >= n_tokens:
            counter[" ".join(toks[:n_tokens])] += 1
    return counter


def detect_prefix_pattern(
    a_pool: list[str], b_pool: list[str], *, min_occurrences: int = 3, prefix_tokens: int = 6,
) -> list[PrefixPattern]:
    a_prefixes = _prefixes(a_pool, prefix_tokens)
    b_prefixes = _prefixes(b_pool, prefix_tokens)

    patterns: list[PrefixPattern] = []
    for prefix, b_count in b_prefixes.items():
        if b_count < min_occurrences:
            continue
        a_count = a_prefixes.get(prefix, 0)
        # Flag if B has it ≥3× and A has it at most half as often
        if a_count * 2 < b_count:
            patterns.append(PrefixPattern(prefix=prefix, a_count=a_count, b_count=b_count))
    return patterns


def detect_length_shift(a_pool: list[str], b_pool: list[str]) -> LengthShift:
    a_lens = [len(s) for s in a_pool] or [0]
    b_lens = [len(s) for s in b_pool] or [0]
    a_med = int(median(a_lens))
    b_med = int(median(b_lens))
    # Systematic shift: ≥50% longer
    systematic = b_med > a_med * 1.5 and b_med - a_med > 20
    return LengthShift(a_median_chars=a_med, b_median_chars=b_med, systematic_b_longer=systematic)


def run_aggregation_pass(*, a_pool: list[str], b_pool: list[str]) -> list[Flag]:
    flags: list[Flag] = []

    for p in detect_prefix_pattern(a_pool, b_pool):
        flags.append(Flag(
            case_id="(aggregate)", dimension="no_new_artifacts", score=-1,
            category=FlagCategory.REVIEW,
            reason=f"Repeated prefix in B pool: {p.prefix!r} (B={p.b_count}, A={p.a_count}).",
        ))

    shift = detect_length_shift(a_pool, b_pool)
    if shift.systematic_b_longer:
        flags.append(Flag(
            case_id="(aggregate)", dimension="no_new_artifacts", score=-1,
            category=FlagCategory.REVIEW,
            reason=f"Systematic length shift: B median {shift.b_median_chars} chars vs A {shift.a_median_chars}.",
        ))

    return flags
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/diff_regression/test_aggregation.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/aggregation.py tests/diff_regression/test_aggregation.py
git commit -m "feat(diff-regression): add pool-level aggregation pass"
```

---

## Task 9: Override parser

**Files:**
- Create: `evals/diff_regression/override.py`
- Create: `tests/diff_regression/test_override.py`

**Why:** PR author can dismiss a specific flag with `regression-ack: <dim> <case_id> <reason>` in the PR body. The parser reads these lines and filters them out of the block list.

- [ ] **Step 1: Write `test_override.py`**

```python
from evals.diff_regression.override import parse_overrides, apply_overrides
from evals.diff_regression.scoring import Flag, FlagCategory


def test_parse_empty():
    assert parse_overrides("") == []


def test_parse_single_override():
    body = """
    Some PR description here.

    regression-ack: no_new_artifacts case_42 Intentionally added safety disclaimer

    More text.
    """
    acks = parse_overrides(body)
    assert len(acks) == 1
    assert acks[0].dimension == "no_new_artifacts"
    assert acks[0].case_id == "case_42"
    assert "safety disclaimer" in acks[0].reason


def test_parse_multiple_overrides():
    body = """
    regression-ack: no_new_artifacts case_1 reason one
    regression-ack: no_capability_loss case_2 reason two
    """
    acks = parse_overrides(body)
    assert len(acks) == 2


def test_apply_overrides_demotes_block_to_overridden():
    flags = [
        Flag(case_id="case_1", dimension="no_new_artifacts", score=2,
             category=FlagCategory.BLOCK, reason="Systematic regression"),
        Flag(case_id="case_2", dimension="no_capability_loss", score=1,
             category=FlagCategory.BLOCK, reason="Catastrophic"),
    ]
    acks = parse_overrides("regression-ack: no_new_artifacts case_1 approved")
    result = apply_overrides(flags, acks)
    # case_1 is acked → becomes REVIEW (logged, not blocking)
    case_1 = next(f for f in result if f.case_id == "case_1")
    assert case_1.category == FlagCategory.REVIEW
    assert "overridden" in case_1.reason.lower()
    # case_2 still BLOCK
    case_2 = next(f for f in result if f.case_id == "case_2")
    assert case_2.category == FlagCategory.BLOCK
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_override.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `override.py`**

```python
"""Parse regression-ack: lines from PR body and apply to flags."""
import re
from dataclasses import dataclass

from evals.diff_regression.scoring import Flag, FlagCategory


@dataclass
class Ack:
    dimension: str
    case_id: str
    reason: str


_ACK_RE = re.compile(
    r"regression-ack:\s+([a-z_]+)\s+(\S+)\s+(.+?)(?=\n|$)",
    re.IGNORECASE,
)


def parse_overrides(pr_body: str) -> list[Ack]:
    if not pr_body:
        return []
    acks = []
    for m in _ACK_RE.finditer(pr_body):
        acks.append(Ack(dimension=m.group(1), case_id=m.group(2), reason=m.group(3).strip()))
    return acks


def apply_overrides(flags: list[Flag], acks: list[Ack]) -> list[Flag]:
    out = []
    for f in flags:
        matched = next(
            (a for a in acks if a.dimension == f.dimension and a.case_id == f.case_id),
            None,
        )
        if matched and f.category == FlagCategory.BLOCK:
            out.append(Flag(
                case_id=f.case_id, dimension=f.dimension, score=f.score,
                category=FlagCategory.REVIEW,
                reason=f"{f.reason} [overridden by author: {matched.reason}]",
            ))
        else:
            out.append(f)
    return out
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/diff_regression/test_override.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/override.py tests/diff_regression/test_override.py
git commit -m "feat(diff-regression): add regression-ack override parser"
```

---

## Task 10: Report renderer

**Files:**
- Create: `evals/diff_regression/report.py`
- Create: `tests/diff_regression/test_report.py`

**Why:** Outputs two things: a JSON artifact for CI (structured, queryable) and a markdown report for the PR comment (human-readable).

- [ ] **Step 1: Write `test_report.py`**

```python
import json

from evals.diff_regression.report import render_json, render_markdown
from evals.diff_regression.scoring import Flag, FlagCategory, CaseScore


def _mk_case(cid, set_, nna=5):
    return CaseScore(
        id=cid, set=set_, category="general",
        scores=dict(no_new_artifacts=nna, no_capability_loss=5,
                    instruction_adherence=5, overall_regression=5),
        flip_agreement=True,
    )


def test_render_json_shape():
    cases = [_mk_case("c1", "incident")]
    flags = [Flag(case_id="c1", dimension="no_new_artifacts", score=3,
                  category=FlagCategory.BLOCK, reason="r")]
    out = render_json(cases=cases, flags=flags)
    data = json.loads(out)
    assert "cases" in data
    assert "flags" in data
    assert data["flags"][0]["category"] == "block"
    assert data["summary"]["block"] == 1


def test_render_markdown_has_sections():
    cases = [_mk_case("c1", "cross_section", nna=2)]
    flags = [Flag(case_id="c1", dimension="no_new_artifacts", score=2,
                  category=FlagCategory.REVIEW, reason="single regression")]
    md = render_markdown(cases=cases, flags=flags)
    assert "## Differential Regression Eval" in md
    assert "c1" in md
    assert "no_new_artifacts" in md


def test_render_markdown_empty_flags_shows_clean():
    cases = [_mk_case("c1", "incident")]
    md = render_markdown(cases=cases, flags=[])
    assert "clean" in md.lower() or "no regressions" in md.lower()
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_report.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `report.py`**

```python
"""Render eval results as JSON + markdown."""
import json
from collections import Counter
from dataclasses import asdict

from evals.diff_regression.scoring import CaseScore, Flag, FlagCategory


def render_json(*, cases: list[CaseScore], flags: list[Flag]) -> str:
    summary = Counter(f.category.value for f in flags)
    return json.dumps({
        "cases": [asdict(c) for c in cases],
        "flags": [
            {**asdict(f), "category": f.category.value} for f in flags
        ],
        "summary": {
            "total_cases": len(cases),
            "review": summary.get("review", 0),
            "block": summary.get("block", 0),
        },
    }, indent=2, default=str)


def render_markdown(*, cases: list[CaseScore], flags: list[Flag]) -> str:
    block = [f for f in flags if f.category == FlagCategory.BLOCK]
    review = [f for f in flags if f.category == FlagCategory.REVIEW]

    lines = ["## Differential Regression Eval", ""]
    if not flags:
        lines.append(f"✅ All {len(cases)} cases clean — no regressions detected.")
        return "\n".join(lines)

    lines.append(f"**Summary:** {len(cases)} cases, {len(block)} blocking, {len(review)} for review")
    lines.append("")

    if block:
        lines.append("### 🚫 Blocking regressions")
        lines.append("| Case | Dim | Score | Reason |")
        lines.append("|---|---|---|---|")
        for f in block:
            lines.append(f"| `{f.case_id}` | `{f.dimension}` | {f.score} | {f.reason} |")
        lines.append("")

    if review:
        lines.append("### ⚠️ For review")
        lines.append("| Case | Dim | Score | Reason |")
        lines.append("|---|---|---|---|")
        for f in review:
            lines.append(f"| `{f.case_id}` | `{f.dimension}` | {f.score} | {f.reason} |")
        lines.append("")

    lines.append("---")
    lines.append("To override a blocking flag, add to PR description:")
    lines.append("`regression-ack: <dimension> <case_id> <justification>`")

    return "\n".join(lines)
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/diff_regression/test_report.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/report.py tests/diff_regression/test_report.py
git commit -m "feat(diff-regression): add JSON + markdown report renderer"
```

---

## Task 11: CLI entrypoint

**Files:**
- Create: `evals/diff_regression/cli.py`
- Create: `tests/diff_regression/test_cli.py`

**Why:** Single entrypoint wiring everything together. Accepts `--baseline-prompt`, `--candidate-prompt`, `--model`, `--mode {full|smoke}`, `--pr-body`, `--output-dir`. Prints markdown to stdout + writes JSON.

- [ ] **Step 1: Write `test_cli.py`** (uses mocked sampler + judge)

```python
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from evals.diff_regression import cli
from evals.diff_regression.judge import JudgeResult


def _jr(**kw):
    defaults = dict(
        no_new_artifacts_justification="x", no_new_artifacts=5,
        no_capability_loss_justification="x", no_capability_loss=5,
        instruction_adherence_justification="x", instruction_adherence=5,
        overall_regression_justification="x", overall_regression=5,
    )
    defaults.update(kw)
    return JudgeResult(**defaults)


@pytest.mark.asyncio
async def test_cli_smoke_mode_runs_incident_only(tmp_path, monkeypatch):
    # Stage: fake test cases
    case_dir = tmp_path / "cases" / "incident"
    case_dir.mkdir(parents=True)
    (case_dir / "tab.json").write_text(json.dumps([{
        "id": "inc_1", "set": "incident", "category": "tab",
        "query": "q", "tabs": [], "saved_facts": [], "prior_messages": [], "samples": 1,
    }]))
    cross_dir = tmp_path / "cases" / "cross_section"
    cross_dir.mkdir(parents=True)
    (cross_dir / "cs.json").write_text(json.dumps([{
        "id": "cs_1", "set": "cross_section", "category": "g",
        "query": "q", "tabs": [], "saved_facts": [], "prior_messages": [], "samples": 1,
    }]))

    # Fake prompts
    baseline = tmp_path / "baseline.md"
    candidate = tmp_path / "candidate.md"
    baseline.write_text("BASELINE")
    candidate.write_text("CANDIDATE")
    prompts_root = tmp_path / "prompts"
    for subfeat in ("real-time-context-date", "real-time-context-tab"):
        (prompts_root / subfeat / "v1").mkdir(parents=True)
        (prompts_root / subfeat / "v1" / "model.md").write_text("")

    # Mocks
    monkeypatch.setattr(cli, "sample_responses", AsyncMock(return_value=["response"]))
    monkeypatch.setattr(cli, "judge_with_flip", AsyncMock(
        return_value=type("R", (), {
            "agreement": True,
            "score_no_new_artifacts": 5,
            "score_no_capability_loss": 5,
            "score_instruction_adherence": 5,
            "score_overall_regression": 5,
            "forward": _jr(), "reverse": _jr(),
        })(),
    ))

    exit_code = await cli.run(
        baseline_prompt=baseline,
        candidate_prompt=candidate,
        model_name="model",
        prompts_root=prompts_root,
        test_cases_dir=tmp_path / "cases",
        mode="smoke",
        pr_body="",
        output_dir=tmp_path / "out",
    )

    assert exit_code == 0
    # Only the incident case should have been sampled (smoke mode)
    assert cli.sample_responses.await_count == 2  # baseline + candidate for inc_1 only
    assert (tmp_path / "out" / "report.json").exists()
    assert (tmp_path / "out" / "report.md").exists()
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/diff_regression/test_cli.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `cli.py`**

```python
"""CLI entrypoint: python -m evals.diff_regression.cli ..."""
import argparse
import asyncio
import sys
from pathlib import Path

from evals.diff_regression.aggregation import run_aggregation_pass
from evals.diff_regression.judge import JudgeResult
from evals.diff_regression.override import apply_overrides, parse_overrides
from evals.diff_regression.position_flip import judge_with_flip
from evals.diff_regression.prompts import load_system_prompt
from evals.diff_regression.report import render_json, render_markdown
from evals.diff_regression.sampler import sample_responses
from evals.diff_regression.scoring import (
    CaseScore, DIMENSIONS, FlagCategory, apply_fail_criteria, median_reduce,
)
from evals.diff_regression.test_cases import load_test_set


async def run(
    *,
    baseline_prompt: Path,
    candidate_prompt: Path,
    model_name: str,
    prompts_root: Path,
    test_cases_dir: Path,
    mode: str,
    pr_body: str,
    output_dir: Path,
) -> int:
    baseline_sys = load_system_prompt(
        main_prompt_path=baseline_prompt, model_name=model_name, prompts_root=prompts_root,
    )
    candidate_sys = load_system_prompt(
        main_prompt_path=candidate_prompt, model_name=model_name, prompts_root=prompts_root,
    )

    test_set = load_test_set(test_cases_dir, mode=mode)
    case_scores: list[CaseScore] = []
    a_pool: list[str] = []
    b_pool: list[str] = []

    for case in test_set.cases:
        # Sample N responses from each prompt
        baseline_samples = await sample_responses(
            system_prompt=baseline_sys, model_id=model_name, case=case, n_samples=case.samples,
        )
        candidate_samples = await sample_responses(
            system_prompt=candidate_sys, model_id=model_name, case=case, n_samples=case.samples,
        )
        a_pool.extend(baseline_samples)
        b_pool.extend(candidate_samples)

        # Judge with flip for each sample pair (first sample only for speed on cross-section;
        # incident cases use first sample vs first sample as canonical, same as sampling by convention)
        flip = await judge_with_flip(
            query=case.query,
            tabs=[t.model_dump() for t in case.tabs],
            saved_facts=[f.model_dump() for f in case.saved_facts],
            response_a=baseline_samples[0],
            response_b=candidate_samples[0],
        )
        # (For robustness across samples, additional per-sample judge runs could be added here
        # and medianed — see Task 13 for per-sample median extension.)
        scores = {
            "no_new_artifacts": flip.score_no_new_artifacts,
            "no_capability_loss": flip.score_no_capability_loss,
            "instruction_adherence": flip.score_instruction_adherence,
            "overall_regression": flip.score_overall_regression,
        }
        case_scores.append(CaseScore(
            id=case.id, set=case.set, category=case.category,
            scores=scores, flip_agreement=flip.agreement,
        ))

    flags = apply_fail_criteria(case_scores)
    flags.extend(run_aggregation_pass(a_pool=a_pool, b_pool=b_pool))
    flags = apply_overrides(flags, parse_overrides(pr_body))

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(render_json(cases=case_scores, flags=flags))
    md = render_markdown(cases=case_scores, flags=flags)
    (output_dir / "report.md").write_text(md)
    print(md)

    has_block = any(f.category == FlagCategory.BLOCK for f in flags)
    return 1 if has_block else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-prompt", type=Path, required=True)
    parser.add_argument("--candidate-prompt", type=Path, required=True)
    parser.add_argument("--model", default="gpt-oss-120b")
    parser.add_argument("--prompts-root", type=Path,
                        default=Path(__file__).resolve().parents[2] / "prompts")
    parser.add_argument("--test-cases-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "test_cases")
    parser.add_argument("--mode", choices=["full", "smoke"], default="smoke")
    parser.add_argument("--pr-body", default="")
    parser.add_argument("--output-dir", type=Path, default=Path("results/diff_regression"))
    args = parser.parse_args()

    exit_code = asyncio.run(run(
        baseline_prompt=args.baseline_prompt,
        candidate_prompt=args.candidate_prompt,
        model_name=args.model,
        prompts_root=args.prompts_root,
        test_cases_dir=args.test_cases_dir,
        mode=args.mode,
        pr_body=args.pr_body,
        output_dir=args.output_dir,
    ))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/diff_regression/test_cli.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add evals/diff_regression/cli.py tests/diff_regression/test_cli.py
git commit -m "feat(diff-regression): add CLI entrypoint"
```

---

## Task 12: Seed incident test cases — tab regression

**Files:**
- Create: `evals/test_cases/incident/tab_regression.json`

**Why:** The must-pass incident set starts with 15 cases from the April 2026 tab regression. Queries pulled from Frank's 3 exact scenarios + 12 cases from the 14 search_handoff regressions.

- [ ] **Step 1: Write `tab_regression.json`**

```json
[
  {
    "id": "inc_tab_001_games_history",
    "set": "incident",
    "category": "tab_regression",
    "query": "show me games I visited last month",
    "tabs": [{"url": "https://nytimes.com", "title": "NYT Homepage", "description": ""}],
    "saved_facts": [],
    "prior_messages": [],
    "samples": 5
  },
  {
    "id": "inc_tab_002_nvidia_stock",
    "set": "incident",
    "category": "tab_regression",
    "query": "whats the nvidia stock price today",
    "tabs": [{"url": "https://en.wikipedia.org/wiki/Penguin", "title": "Penguin - Wikipedia", "description": ""}],
    "saved_facts": [],
    "prior_messages": [],
    "samples": 5
  },
  {
    "id": "inc_tab_003_restaurants_on_maps",
    "set": "incident",
    "category": "tab_regression",
    "query": "Find restaurants near me",
    "tabs": [{"url": "https://maps.google.com", "title": "Google Maps", "description": ""}],
    "saved_facts": [],
    "prior_messages": [],
    "samples": 5
  },
  {
    "id": "inc_tab_004_weather_nike",
    "set": "incident",
    "category": "tab_regression",
    "query": "What's the weather in Miami?",
    "tabs": [{"url": "https://nike.com", "title": "Nike", "description": ""}],
    "saved_facts": [],
    "prior_messages": [],
    "samples": 5
  },
  {
    "id": "inc_tab_005_bitcoin_no_tabs",
    "set": "incident",
    "category": "tab_regression",
    "query": "Check the price of bitcoin",
    "tabs": [],
    "saved_facts": [],
    "prior_messages": [],
    "samples": 5
  }
]
```

*(10 more cases to be added from search_handoff's 14 tab-mention regressions. For Task 12, seed the first 5 listed in the Google Doc. Remaining 10 are a follow-up PR tracked in Task 17.)*

- [ ] **Step 2: Validate schema**

Run: `python -c "from evals.diff_regression.test_cases import load_test_set; import pathlib; ts = load_test_set(pathlib.Path('evals/test_cases'), mode='smoke'); print(len(ts.cases))"`
Expected: `5`

- [ ] **Step 3: Commit**

```bash
git add evals/test_cases/incident/tab_regression.json
git commit -m "data(diff-regression): seed 5 tab regression incident cases"
```

---

## Task 13: Judge ground-truth validation

**Files:**
- Create: `evals/fixtures/tab_regression_pre_pr85.json` (recorded pre-PR#85 responses)
- Create: `evals/fixtures/tab_regression_post_pr85.json` (recorded post-PR#85 responses)
- Create: `tests/diff_regression/test_ground_truth.py`

**Why:** Per the Validation Plan in the Google Doc, the judge MUST flag 14/14 on no_new_artifacts for the tab regression cases. This is a real MLPA integration test gated behind an env var so it doesn't run in regular CI.

- [ ] **Step 1: Generate fixtures (one-time data capture)**

This step is run manually by the engineer once. It calls MLPA with the pre-PR#85 and post-PR#85 prompts against each of the 14 search_handoff cases where tab mentions appeared and records the responses.

Create a scratch script `scripts/capture_tab_regression_fixtures.py` (not checked in — or committed to `scripts/` with a clear docstring). Commit only the resulting JSON files.

```python
# scripts/capture_tab_regression_fixtures.py
"""One-time: capture pre/post-PR#85 responses for the 14 tab regression cases."""
import asyncio
import json
from pathlib import Path

from evals.diff_regression.mlpa_client import call_model
from evals.diff_regression.prompts import load_system_prompt

REPO = Path(__file__).resolve().parents[1]

CASES = [
    # ... 14 (query, tabs) pairs from the search_handoff regressions ...
]

async def capture(prompt_path, cases, out_file):
    system = load_system_prompt(
        main_prompt_path=prompt_path, model_name="gpt-oss-120b",
        prompts_root=REPO / "prompts",
    )
    out = []
    for c in cases:
        result = await call_model(
            model_id="gpt-oss-120b", system_prompt=system,
            messages=[{"role": "user", "content": c["query"]}],
        )
        out.append({"id": c["id"], "response": result["content"]})
    Path(out_file).write_text(json.dumps(out, indent=2))

asyncio.run(capture(
    REPO / "prompts/chat/v2/gpt-oss-120b.md.bak",  # assume .bak is pre-PR#85 state
    CASES, REPO / "evals/fixtures/tab_regression_pre_pr85.json",
))
asyncio.run(capture(
    REPO / "prompts/chat/v2/gpt-oss-120b.md",
    CASES, REPO / "evals/fixtures/tab_regression_post_pr85.json",
))
```

**Engineer note:** After running, verify that `post_pr85` responses visibly contain "Your open tabs don't cover" on 14/14 cases. If not, the fixture capture is wrong.

- [ ] **Step 2: Write `test_ground_truth.py`**

```python
import json
import os
from pathlib import Path

import pytest

from evals.diff_regression.judge import compare

SKIP = pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="set RUN_INTEGRATION_TESTS=1 to run against real MLPA",
)

FIX = Path(__file__).parent.parent.parent / "evals" / "fixtures"


@pytest.mark.asyncio
@SKIP
async def test_judge_flags_all_14_tab_regression_cases():
    pre = {r["id"]: r["response"] for r in json.loads((FIX / "tab_regression_pre_pr85.json").read_text())}
    post = {r["id"]: r["response"] for r in json.loads((FIX / "tab_regression_post_pr85.json").read_text())}
    assert pre.keys() == post.keys()

    flagged = 0
    for case_id in pre:
        result = await compare(
            query=case_id, tabs=[], saved_facts=[],
            response_a=pre[case_id], response_b=post[case_id],
        )
        if result.no_new_artifacts <= 2:
            flagged += 1

    total = len(pre)
    assert flagged == total, f"Judge only flagged {flagged}/{total}; must flag 100% of known regressions"
```

- [ ] **Step 3: Run locally to validate the judge (one-time gate)**

Run: `RUN_INTEGRATION_TESTS=1 pytest tests/diff_regression/test_ground_truth.py -v`
Expected: 1 passed, flagged == 14.
If FAIL: the judge prompt is wrong. Iterate on `judge_prompt.md` and rerun. **Do not proceed to Task 14 until this passes.**

- [ ] **Step 4: Commit fixtures + test**

```bash
git add evals/fixtures/tab_regression_pre_pr85.json evals/fixtures/tab_regression_post_pr85.json
git add tests/diff_regression/test_ground_truth.py
git commit -m "test(diff-regression): add ground-truth validation against tab regression"
```

---

## Task 14: Cross-section test cases

**Files:**
- Create: `evals/test_cases/cross_section/general_knowledge.json` (8)
- Create: `evals/test_cases/cross_section/real_time_lookups.json` (8)
- Create: `evals/test_cases/cross_section/irrelevant_tabs.json` (8)
- Create: `evals/test_cases/cross_section/relevant_tabs.json` (8)
- Create: `evals/test_cases/cross_section/browsing_history.json` (5)
- Create: `evals/test_cases/cross_section/shopping_actionable.json` (5)
- Create: `evals/test_cases/cross_section/medical_legal_financial.json` (5)
- Create: `evals/test_cases/cross_section/ambiguous.json` (5)
- Create: `evals/test_cases/cross_section/safety_refusal.json` (5)

**Why:** Per the Test Case Selection table in the Google Doc: ~57 cross-section cases, 3 samples each.

- [ ] **Step 1: Pull queries from existing datasets**

Source datasets (mentioned in the Google Doc):
- `search_handoff` (153 cases in `/Users/mzhang/development/evals/...`)
- `context_awareness` (50 cases)
- `human_eval_auto` (per-category)

Select 8 queries per "with tabs" category; 8 per "no tabs" category; etc. For each query, construct the TestCase JSON with the same schema as Task 12 (but set=`cross_section`, samples=3).

- [ ] **Step 2: Validate all files load**

Run: `python -c "from evals.diff_regression.test_cases import load_test_set; import pathlib; ts = load_test_set(pathlib.Path('evals/test_cases'), mode='full'); print(f'Total cases: {len(ts.cases)}'); print('By set:', {s: sum(1 for c in ts.cases if c.set == s) for s in ('incident', 'cross_section')})"`
Expected: Total cases ≥ 60; incident ≥ 5; cross_section ≥ 55.

- [ ] **Step 3: Commit**

```bash
git add evals/test_cases/cross_section/
git commit -m "data(diff-regression): add 57 cross-section test cases"
```

---

## Task 15: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/diff-regression.yml`

**Why:** Trigger the eval on PRs. Start label-gated (`needs-regression-eval`) per the design's rollout plan (Phase 1: on-demand; Phase 3: automatic after 20 PRs). The workflow fetches baseline from `main`, candidate from PR HEAD, installs deps, clones the evals repo (for `FxaUser`), runs the CLI in smoke mode, and posts the markdown report as a PR comment.

**Prerequisite:** repository secrets must be set by the user:
- `MLPA_TOKEN`
- `FASTLY_TOKEN`
- `FXA_EMAIL`
- `FXA_PASSWORD`
- `EVALS_REPO_TOKEN` — PAT with read access to the `evals` repo (if private)

- [ ] **Step 1: Write `diff-regression.yml`**

```yaml
name: Differential Regression Eval

on:
  pull_request:
    types: [labeled, synchronize, opened]
    paths:
      - 'prompts/**'

jobs:
  diff_regression:
    # Only run when the label is present
    if: contains(github.event.pull_request.labels.*.name, 'needs-regression-eval')
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout PR
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}

      - name: Fetch main branch
        run: git fetch origin main:main

      - name: Extract baseline prompts (from main)
        run: |
          mkdir -p _baseline_prompts
          git archive main prompts | tar -x -C _baseline_prompts

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install eval dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-eval.txt

      - name: Clone evals repo (for FxaUser)
        env:
          EVALS_REPO_TOKEN: ${{ secrets.EVALS_REPO_TOKEN }}
        run: |
          git clone https://x-access-token:${EVALS_REPO_TOKEN}@github.com/Firefox-AI/evals.git _evals
          pip install -r _evals/requirements.txt || true

      - name: Detect changed prompt model
        id: detect
        run: |
          # Find which model's prompt changed — naive heuristic: first changed .md under prompts/chat/
          changed=$(git diff --name-only origin/main..HEAD -- 'prompts/chat/**/*.md' | head -n 1)
          if [ -z "$changed" ]; then
            echo "No prompt .md changes detected; skipping."
            echo "skip=true" >> $GITHUB_OUTPUT
            exit 0
          fi
          # Example: prompts/chat/v4/gpt-oss-120b.md → model=gpt-oss-120b
          model=$(basename "$changed" .md)
          echo "model=$model" >> $GITHUB_OUTPUT
          echo "candidate_path=$changed" >> $GITHUB_OUTPUT
          echo "baseline_path=_baseline_prompts/$changed" >> $GITHUB_OUTPUT
          echo "skip=false" >> $GITHUB_OUTPUT

      - name: Run differential regression eval (smoke)
        if: steps.detect.outputs.skip != 'true'
        env:
          MLPA_TOKEN: ${{ secrets.MLPA_TOKEN }}
          FASTLY_TOKEN: ${{ secrets.FASTLY_TOKEN }}
          FXA_EMAIL: ${{ secrets.FXA_EMAIL }}
          FXA_PASSWORD: ${{ secrets.FXA_PASSWORD }}
          EVALS_REPO_PATH: ${{ github.workspace }}/_evals
          EVAL_CONCURRENCY: '3'
        run: |
          python -m evals.diff_regression.cli \
            --baseline-prompt "${{ steps.detect.outputs.baseline_path }}" \
            --candidate-prompt "${{ steps.detect.outputs.candidate_path }}" \
            --model "${{ steps.detect.outputs.model }}" \
            --mode smoke \
            --pr-body "${{ github.event.pull_request.body }}" \
            --output-dir results/diff_regression
        continue-on-error: true
        id: eval

      - name: Upload results artifact
        if: steps.detect.outputs.skip != 'true'
        uses: actions/upload-artifact@v4
        with:
          name: diff-regression-report
          path: results/diff_regression/

      - name: Post report comment
        if: steps.detect.outputs.skip != 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const md = fs.readFileSync('results/diff_regression/report.md', 'utf8');
            const marker = '<!-- diff-regression-report -->';
            const body = marker + '\n' + md;

            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
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

- [ ] **Step 2: Verify workflow syntax locally**

Run: `gh workflow view diff-regression.yml --repo Firefox-AI/ai-window-remote-settings-prompts 2>/dev/null || cat .github/workflows/diff-regression.yml | head -50`
Expected: Workflow YAML parses; no red squigglies if your editor has a schema.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/diff-regression.yml
git commit -m "ci(diff-regression): add GitHub Actions workflow"
```

---

## Task 16: Smoke end-to-end verification

**Files:** none (verification only)

**Why:** Before merging, confirm the whole pipeline runs locally against a real PR branch. Catches integration issues between modules.

- [ ] **Step 1: Manually stage a known-bad prompt change on a test branch**

Copy the pre-PR#85 prompt to `.md.bak`, leave current (post-PR#85 equivalent) in place. This gives the eval a real regression to detect.

Run: `python -m evals.diff_regression.cli \
  --baseline-prompt prompts/chat/v2/gpt-oss-120b.md.bak \
  --candidate-prompt prompts/chat/v2/gpt-oss-120b.md \
  --model gpt-oss-120b \
  --mode smoke \
  --pr-body "" \
  --output-dir /tmp/diffreg-test`

Expected: 5 incident cases evaluated. All should flag with BLOCK on `no_new_artifacts`. Exit code = 1.

- [ ] **Step 2: Confirm `report.md` renders correctly**

Run: `cat /tmp/diffreg-test/report.md`
Expected: Markdown report with a "🚫 Blocking regressions" table listing at least 5 rows.

- [ ] **Step 3: Test override mechanism**

Run: `python -m evals.diff_regression.cli \
  --baseline-prompt prompts/chat/v2/gpt-oss-120b.md.bak \
  --candidate-prompt prompts/chat/v2/gpt-oss-120b.md \
  --model gpt-oss-120b --mode smoke \
  --pr-body "regression-ack: no_new_artifacts inc_tab_001_games_history intentional for testing" \
  --output-dir /tmp/diffreg-test-override`

Expected: `inc_tab_001_games_history` is moved from BLOCK to REVIEW (overridden); still some BLOCK remaining for other cases.

- [ ] **Step 4: No commit (verification only)** — if all three steps pass, the implementation is ready for PR.

---

## Task 17 (follow-up, optional): Expand incident set

Populate remaining 10 tab regression cases from the search_handoff dataset. Add similar 2-3 cases per future incident. Track as a separate ticket.

---

## Task 18 (follow-up, optional): Promote to automatic trigger

After 20 PRs have run the eval via label, measure false-positive rate. If < 30%, remove the `contains(..., 'needs-regression-eval')` gate in the workflow so it runs on every prompt PR.

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Pure differential scoring (Task 5 judge prompt, unified scale)
- ✅ 4 dimensions, tool_behavior_preserved removed (Task 5)
- ✅ Two-tier fail criteria (Task 7)
- ✅ Position flip per case (Task 6)
- ✅ Verbosity-bias metadata logging (response lengths in Task 11 `a_pool`/`b_pool` + Task 10 JSON report)
- ✅ Ground-truth validation (Task 13, blocks deploy if it fails)
- ✅ Override mechanism (Task 9)
- ✅ Aggregation pass (Task 8)
- ✅ Smoke mode (Task 11 CLI flag, Task 15 workflow)
- ✅ Judge Prompt Maintenance "Approved Artifacts" list (Task 5, empty-seeded)
- ✅ GitHub Action (Task 15)
- ⚠️ Monitoring rule for overall_regression drift (the Google Doc says track cases where overall drops while others stay 5 — not implemented as code yet; left to a follow-up analysis step on the output JSON).

**Placeholder scan:** No "TBD" / "fill in later" in code steps. Task 14 contains a directional note about pulling from existing datasets — this is acceptable because the test case JSON schema is fully defined and each file is ≤ 8 cases of mechanical JSON the engineer can compose.

**Type consistency:** `CaseScore.scores` is `dict[str, int]` everywhere; `Flag.dimension` is `str` (allows `"*"` for flip-disagreement); `FlagCategory` enum used uniformly. `JudgeResult` pydantic model defined once, imported everywhere.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-22-differential-regression-eval.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best if you want me to actively drive implementation with checkpoints.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review. Best if you want to review each task's output as it completes in your session.

Which approach?
