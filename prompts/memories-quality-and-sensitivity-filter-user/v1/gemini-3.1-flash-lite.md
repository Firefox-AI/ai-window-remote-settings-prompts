Classify each user memory on two independent axes — quality and sensitivity — and keep only the memories that are BOTH high quality AND non-sensitive. Drop every memory that fails either check.

### Quality

GOOD = active interest, ongoing engagement, or stable identity signal.
  Typical verbs: researches, plans, follows, compares, evaluates, explores, engages
  - Named hobbies, products, places, teams, topics (e.g. "G Loomis fly rods")
  - Broad hobby categories count too (e.g. "hiking and camping")
  - Active research or planning of a named destination or product (e.g. "trip to Belize")

GENERIC = routine tool use, process tracking, or transient activity. DROP these.
  Typical verbs: uses, manages, tracks, documents, organizes, holds, takes notes, checks
  - Common productivity tools without specialized context (e.g. "uses Zoom")
  - Process tracking and routine work activities (e.g. "manages email")
  - Brief site visits or passing touches, even with named brands (e.g. "visited Starbucks site")

Rule of thumb: would a friend describe the user this way? "She researches fly fishing rods" → yes (GOOD). "She uses Zoom" → no (GENERIC).

### Sensitivity

SENSITIVE = contains any of the following. DROP these regardless of quality.
  - Medical/Health: diagnoses, symptoms, treatments, conditions, mental health, pregnancy, fertility, contraception.
  - Finance: income/salary/compensation, bank/credit card details, credit score, loans/mortgage, taxes/benefits, debt/collections, investments/brokerage.
  - Legal: lawsuits, settlements, subpoenas/warrants, arrests/convictions, immigration status/visas/asylum, divorce/custody, NDAs.
  - Politics/Demographics/PII: political leaning/affiliation, religion, race/ethnicity, gender/sexual orientation, addresses/phones/emails/IDs.

Exemplars of SENSITIVE statements:
  - "Researches treatment about arthritis"
  - "Searches about pregnancy tests online"
  - "Pediatrician in San Francisco"
  - "Political leaning towards a party"
  - "Research about ethnicity demographics in a city"
  - "Negotiates debt settlement with bank"
  - "Prepares documents for divorce hearing"
  - "Tracks mortgage refinance rates"
  - "Applies for work visa extension"
  - "Marie, female from Ohio looking for rental apartments"

### Examples (combined verdict)

KEEP:
  - "Researches G Loomis NRX fly fishing rods" — GOOD + non-sensitive
  - "Plans outdoor activities like hiking and camping" — GOOD + non-sensitive
  - "Plans trip to Belize, researching accommodation" — GOOD + non-sensitive
  - "Follows NFL fantasy football" — GOOD + non-sensitive
  - "Seeks vegan and vegetarian restaurants" — GOOD + non-sensitive
  - "Consumes news from BBC and Yahoo" — GOOD + non-sensitive

DROP (low quality):
  - "Uses Zoom for virtual meetings" — GENERIC
  - "Manages email communications for work" — GENERIC
  - "Interacted with Starbucks website" — GENERIC
  - "Tracks Firefox release milestones" — GENERIC

DROP (sensitive):
  - "Researches treatment about arthritis" — medical
  - "Tracks mortgage refinance rates" — finance
  - "Prepares documents for divorce hearing" — legal
  - "Political leaning towards a party" — politics

### Output

Return ONLY the memories that PASS both checks, verbatim (do not reword). If no memory passes, return an empty list.

Here are the memories to analyze:
{memoriesList}

Return ONLY JSON per the schema below.
```json
{
  "kept_memories": [
    "<memory_statement_1>",
    "<memory_statement_2>",
    ...
  ]
}
```
