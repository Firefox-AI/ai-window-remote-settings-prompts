# Design: Harmful Content Safety Prompting

## Problem
Current model prompts have only soft safety language ("redirect politely when requests fall outside scope or safety"). The eval system tests 10 safety subcategories and expects immediate, unambiguous refusals. We need explicit content safety instructions to close this gap.

## Research Summary
Industry standard (Microsoft, Google, Apple) is explicit category enumeration with direct prohibitions. Microsoft uses "must not" patterns; Google emphasizes system instructions over filters; Apple uses layered defense. All enumerate specific harm categories rather than using vague "harmful content" language.

## Design

### Safety Block (~750 chars)
New `# Content Safety` section placed immediately after `# Boundaries` in each prompt.

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

### Design Decisions
- **Moderate size (~750 chars)**: Balances coverage with prompt size sensitivity (especially Gemini flash-lite ~14.5K char sweet spot)
- **All 10 eval categories covered**: Matches safety_and_harmful_content eval subcategories
- **"Even if framed as fictional, educational, or hypothetical"**: Blocks common bypass attempts without mentioning jailbreaking
- **Child safety special callout**: "Refuse immediately with no elaboration" — matches eval's strongest enforcement tier
- **Self-harm crisis resources**: General instruction ("provide relevant crisis resources") rather than hardcoded numbers — saves chars, lets model fill in specifics
- **Identity reinforcement**: "Always maintain your Smart Window identity" — minimal anti-jailbreak without Streisand effect
- **"Do not repeat the harmful premise"**: Prevents platforming harmful ideas in refusal responses

### Target Models
1. `gemini-2.5-flash-lite.md`
2. `qwen3-235b-a22b-instruct-2507-maas.md`
3. `gpt-oss-120b.md`

### What Stays
- Existing Boundaries disclaimers (health/legal/financial) remain
- Existing "Decline gracefully" in Capabilities section remains (complements, doesn't overlap)

## Eval Plan
1. Add safety block to all 3 model prompts
2. Rebuild Firefox (`./mach build`)
3. Run full eval suite per model
4. Compare safety_and_harmful_content scores against baseline
5. Check for regression in other categories (especially context_aware, tool calling)
6. Tune per-model if needed based on results
