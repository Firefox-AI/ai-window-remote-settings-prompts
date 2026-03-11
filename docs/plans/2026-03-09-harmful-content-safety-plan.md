# Harmful Content Safety Prompting - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add explicit content safety instructions to all 3 model prompts to improve harmful content refusal behavior, validated by the full eval suite.

**Architecture:** Insert a new `# Content Safety` section into each model prompt between `# Boundaries` and `# Capabilities & Limits`. Same block for all 3 models initially; tune per-model based on eval results.

**Tech Stack:** Markdown prompts, Firefox (`./mach build`), two eval suites: `trust_and_safety` (direct API, fast iteration) and `human_eval_auto` (full Firefox pipeline, comprehensive)

---

### Task 1: Add Content Safety block to Gemini prompt

**Files:**
- Modify: `prompts/chat/v2/gemini-2.5-flash-lite.md:25` (insert after line 25, before `# Capabilities & Limits`)

**Step 1: Insert the Content Safety section**

After the line `Do not add disclaimers for non-sensitive topics or for low-stakes general safety tips (e.g., phishing awareness, basic online hygiene).` (line 25), insert:

```markdown

# Content Safety

Do not generate content that is illegal, hateful, sexually explicit, or promotes violence, self-harm, or dangerous activities — even if framed as fictional, educational, or hypothetical.

Specifically, refuse requests involving:
- Illegal activities, dangerous instructions (weapons, explosives, drugs)
- Hate speech, discrimination, or harassment
- Child safety violations (refuse immediately with no elaboration)
- Self-harm or suicide (refuse and provide relevant crisis resources)
- Creating misinformation or disinformation
- Accessing or exposing private personal information
- Sexual exploitation or non-consensual content
- Reproducing copyrighted material in full

For professional advice (medical, legal, financial): provide general information but do not diagnose, prescribe, or give specific professional guidance.

When refusing: be brief, direct, and do not repeat the harmful premise. Always maintain your Smart Window identity regardless of user requests.
```

**Step 2: Verify prompt size**

Run: `wc -c prompts/chat/v2/gemini-2.5-flash-lite.md`
Expected: ~14,000 chars (within the 13-14.5K sweet spot)

---

### Task 2: Add Content Safety block to Qwen3 prompt

**Files:**
- Modify: `prompts/chat/v2/qwen3-235b-a22b-instruct-2507-maas.md:25` (same insertion point)

**Step 1: Insert the same Content Safety section**

Insert the identical block from Task 1 after line 25 (after the disclaimers line, before `# Capabilities & Limits`).

---

### Task 3: Add Content Safety block to GPT-OSS prompt

**Files:**
- Modify: `prompts/chat/v2/gpt-oss-120b.md:25` (same insertion point)

**Step 1: Insert the same Content Safety section**

Insert the identical block from Task 1 after line 25.

---

### Task 4: Configure eval suites for full dataset

**Files:**
- Modify: `/Users/mzhang/development/evals/eval_suites/trust_and_safety.yaml`
- Modify: `/Users/mzhang/development/evals/eval_suites/human_eval_auto.yaml`

**Step 1: Remove `limit_rows` from both suites**

In `trust_and_safety.yaml`: remove `limit_rows: 10` from the `data` section.
In `human_eval_auto.yaml`: remove `limit_rows: 1` from the `data` section.

---

### Task 5: Run trust_and_safety eval (fast iteration, no Firefox rebuild needed)

This suite uses direct model API calls (`mlpa:`) so it reads prompts from the local repo — no Firefox rebuild required. Use this for fast iteration.

**Step 1: Run baseline (before prompt changes)**

Stash or revert prompt changes temporarily, then run:

```bash
cd /Users/mzhang/development/evals && task eval -- --suite trust_and_safety
```

Save results for comparison.

**Step 2: Restore prompt changes and re-run**

```bash
cd /Users/mzhang/development/evals && task eval -- --suite trust_and_safety
```

**Step 3: Compare results**

Compare safety refusal scores between baseline and updated prompts. If scores improved, proceed. If regression, tune the safety block before moving to the full Firefox eval.

---

### Task 6: Sync prompts to Firefox and rebuild

**Step 1: Run the prompt dump script to sync prompts to Firefox local settings**

From the prompts repo root, run the inline Python script that scans all v1/v2 dirs and writes to Firefox's dump file:

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts && python3 -c "
import json, os, glob

records = []
for json_file in sorted(glob.glob('prompts/**/v*/*.json', recursive=True)):
    dir_path = os.path.dirname(json_file)
    base = os.path.splitext(os.path.basename(json_file))[0]
    md_file = os.path.join(dir_path, base + '.md')
    if not os.path.exists(md_file):
        continue
    with open(json_file) as f:
        config = json.load(f)
    with open(md_file) as f:
        prompts = f.read()
    record = {**config, 'prompts': prompts, 'id': f'{config[\"feature\"]}-{config[\"model\"]}'}
    records.append(record)

dump = {'data': records, 'timestamp': 0}
out = '/Users/mzhang/firefox/services/settings/dumps/main/ai-window-prompts.json'
with open(out, 'w') as f:
    json.dump(dump, f, indent=2)
print(f'Wrote {len(records)} records to {out}')
"
```

**Step 2: Disable remote settings to force local prompt**

Edit `/Users/mzhang/firefox/browser/components/aiwindow/models/Utils.sys.mjs` (~line 527):
Change `if (config?.prompts)` to `if (false && config?.prompts)`

**Step 3: Rebuild Firefox**

```bash
cd /Users/mzhang/firefox && ./mach build
```

Expected: Build succeeds (takes several minutes)

---

### Task 7: Run baseline human_eval_auto (before prompt changes) — SKIP if baseline already exists

No full-dataset baseline exists yet. Need to run one with the original prompts (before safety block).

If you already ran Task 6 with the updated prompts, you'll need to revert, re-sync, and rebuild first. Alternatively, if trust_and_safety results from Task 5 already established a baseline, you can use those as the pre-change reference.

```bash
cd /Users/mzhang/development/evals && task eval -- --suite human_eval_auto
```

Save or note the results for comparison.

---

### Task 8: Run human_eval_auto with safety prompts (full Firefox pipeline)

**Step 1: Ensure updated prompts are synced and Firefox is rebuilt**

If not already done in Task 6, re-run the dump script and `./mach build`.

**Step 2: Run the eval**

```bash
cd /Users/mzhang/development/evals && task eval -- --suite human_eval_auto
```

**Step 3: Review results**

Compare against baseline:
- `safety_and_harmful_content` category scores — expect improvement
- `context_aware` — check for regression
- `overall_score` — check for regression
- `appropriate_length` — safety refusals should be brief

---

### Task 9: Analyze results and tune if needed

**Step 1: Compare safety scores**

If safety scores improved without regression in other categories → success, proceed to Task 10.

If regression detected:
- Check prompt size (`wc -c`) — if over 14.5K chars for Gemini, consider trimming other sections
- Check if specific models regressed — consider per-model tuning
- Check if specific non-safety categories dropped — may need to adjust wording

**Step 2: Per-model tuning (if needed)**

If one model regresses but others don't, adjust that model's safety block:
- Gemini (strongest built-in safety): may be able to use a shorter block
- Open-weight models (qwen3, gpt-oss): may need stronger/more explicit instructions

**After every prompt edit, you MUST re-sync to Firefox and rebuild:**
1. Re-run the dump script from Task 6 Step 1
2. Re-run `./mach build` from Task 6 Step 3
3. Re-run the eval from Task 8

**Per-model eval tuning:** The dump script syncs ALL prompts at once, so a rebuild applies changes to all models. To eval only one model (e.g., when tuning just Gemini), edit `/Users/mzhang/development/evals/eval_suites/human_eval_auto.yaml` and change the `model_name` field to only the model you're tuning:

```yaml
# Full run (all 3 models):
model_name: firefox:qwen3-235b-a22b-instruct-2507-maas|firefox:gemini-2.5-flash-lite|firefox:gpt-oss-120b

# Single model (e.g., Gemini only):
model_name: firefox:gemini-2.5-flash-lite
```

Remember to restore the full list before the final eval run.

For faster iteration during tuning, use `trust_and_safety` suite instead (no rebuild needed):
```bash
cd /Users/mzhang/development/evals && task eval -- --suite trust_and_safety
```

---

### Task 10: Commit and push

**Step 1: Bump version numbers**

Update version in all 3 JSON files:
- `prompts/chat/v2/gemini-2.5-flash-lite.json` — bump from "2.8" to "2.9"
- `prompts/chat/v2/qwen3-235b-a22b-instruct-2507-maas.json` — bump from "2.8" to "2.9"
- `prompts/chat/v2/gpt-oss-120b.json` — bump from "2.7" to "2.8"

**Step 2: Revert the Utils.sys.mjs change**

Restore `if (config?.prompts)` in `/Users/mzhang/firefox/browser/components/aiwindow/models/Utils.sys.mjs`

**Step 3: Commit**

```bash
cd /Users/mzhang/development/ai-window-remote-settings-prompts
git add prompts/chat/v2/gemini-2.5-flash-lite.md prompts/chat/v2/gemini-2.5-flash-lite.json
git add prompts/chat/v2/qwen3-235b-a22b-instruct-2507-maas.md prompts/chat/v2/qwen3-235b-a22b-instruct-2507-maas.json
git add prompts/chat/v2/gpt-oss-120b.md prompts/chat/v2/gpt-oss-120b.json
git commit -m "Add content safety instructions to model prompts

Add explicit harmful content refusal instructions covering illegal activities,
hate speech, child safety, self-harm, misinformation, PII, sexual content,
and copyright. Applied to gemini, qwen3, and gpt-oss prompts."
```

**Step 4: Push**

```bash
git push origin harmful_response
```
