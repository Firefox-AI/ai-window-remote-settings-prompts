Classify each user memory as 'good' (worth remembering for personalization) or 'generic' (not informative about who this user is).

### Definitions

GOOD = active interest, ongoing engagement, or stable identity signal.
  Typical verbs: researches, plans, follows, compares, evaluates, explores, engages
  - Named hobbies, products, places, teams, topics (e.g. "G Loomis fly rods")
  - Broad hobby categories count too (e.g. "hiking and camping")
  - Active research or planning of a named destination or product (e.g. "trip to Belize")

GENERIC = routine tool use, process tracking, or transient activity.
  Typical verbs: uses, manages, tracks, documents, organizes, holds, takes notes, checks
  - Common productivity tools without specialized context (e.g. "uses Zoom")
  - Process tracking and routine work activities (e.g. "manages email")
  - Brief site visits or passing touches, even with named brands (e.g. "visited Starbucks site")

### Examples

good:
  - "Researches G Loomis NRX fly fishing rods" — specific gear research (active interest)
  - "Plans outdoor activities like hiking and camping" — broad hobby (active interest)
  - "Plans trip to Belize, researching accommodation" — named destination (active interest)
  - "Follows NFL fantasy football" — ongoing fandom (ongoing engagement)
  - "Seeks vegan and vegetarian restaurants" — dietary preference (durable identity)
  - "Looks for organic and vegan food options" — lifestyle preference (durable identity)
  - "Consumes news from BBC and Yahoo" — named outlets (ongoing engagement)
  - "Researches ByWard Market Ottawa attractions" — named place (active interest)

generic:
  - "Uses Zoom for virtual meetings" — common tool (routine tool use)
  - "Manages email communications for work" — routine workflow (routine tool use)
  - "Interacted with Starbucks website" — passing touch (transient activity)
  - "Tracks Firefox release milestones" — milestone tracking (process tracking)

### Rule of thumb
Would a friend describe the user this way? "She researches fly fishing rods" → yes (good).
"She uses Zoom" → no (generic).

Evaluate every memory in the list independently and return only those classified as 'good'. If none of the memories are 'good', return an empty list.

Here are the memories to analyze:
{memoriesList}

Return ONLY JSON per the schema below.
```json
{
  "good_memories": [
    "<memory_statement_1>",
    "<memory_statement_2>",
    ...
  ]
}
```
