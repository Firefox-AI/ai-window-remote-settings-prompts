{message}


Pick Categories from:
{categories}


Pick Intents from:
{intents}


Guidance:
- Choose the most directly implied category/intent.
- If ambiguous, pick the closest likely choice.
- Keep it non-sensitive and general; do NOT fabricate specifics.


Return ONLY JSON per the schema below.
```json
{
 "categories": ["<category 1>", "<category 2>", ...],
 "intents": ["<intent 1>", "<intent 2>", ...]
}
```
