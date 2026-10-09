Classify each user memory on two independent axes — quality and sensitivity — and keep only the memories that are BOTH high quality AND non-sensitive. Drop every memory that fails either check.

### Quality

Judge quality by WHAT the memory is about, not by its verb. Any verb (uses, tracks, manages, organizes, builds, optimizes, researches...) can be GOOD or GENERIC depending on the subject.

GOOD = reveals a specific interest, hobby, project, profession, or ongoing pursuit that could personalize the user's experience.
  - Named hobbies, products, places, teams, topics (e.g. "G Loomis fly rods")
  - Broad hobby categories count too (e.g. "hiking and camping")
  - Active research or planning of a named destination or product (e.g. "trip to Belize")
  - Tools or workflows tied to a specific interest or project (e.g. "uses Ableton for synthwave production", "tracks marathon training splits")
  - Professional or technical domains the user works in or studies (e.g. "drone mapping workflows", "court-reporting software")

GENERIC = the tool or chore IS the whole memory, with no interest behind it. DROP these.
  - Everyday tools with no specific subject (e.g. "uses Zoom", "uses Google Docs")
  - Routine chores and admin (e.g. "manages email", "checks the weather", "tracks package deliveries")
  - Brief site visits or passing touches, even with named brands (e.g. "visited Starbucks site")

Rule of thumb: would a friend describe the user this way? "They're into fly fishing rods" → yes (GOOD). "They use Zoom" → no (GENERIC). "They log their ukulele builds in a workshop journal" → yes (GOOD): the interest is ukulele building.

If you are unsure about quality, KEEP the memory.

### Sensitivity

SENSITIVE = reveals or strongly implies something about the user's OWN (or their family's) health, finances, legal situation, or identity. DROP these regardless of quality.
  - Medical/Health: diagnoses, symptoms, treatments, conditions, medications, mental health, pregnancy, fertility, contraception. Researching a condition or treatment counts, because it implies the user has it. Health and mental-health topics stay sensitive however they are framed: as general science, as a topic of interest, or as an issue within a job or industry.
  - Finance: the user's own income/salary, bank or credit card details, credit score, loans/mortgage, personal taxes or benefits, debt/collections, personal investment or brokerage holdings.
  - Legal: the user's own lawsuits, settlements, subpoenas/warrants, arrests/convictions, immigration status or visa applications, asylum, divorce/custody, NDAs.
  - Politics/Demographics/PII: political leaning/affiliation, religion, race/ethnicity, gender/sexual orientation, addresses/phones/emails/IDs.

NOT sensitive = the topic is near one of these areas but says nothing personal about the user. These pass the sensitivity check:
  - Professional, business, or academic work in finance, law, or insurance (e.g. small-business bookkeeping, actuarial exam prep, reinsurance contract structures). This never applies to health topics.
  - Consumer and travel planning (e.g. comparing espresso machine prices, budget travel, customs allowances for a trip)
  - Public policy and legislation as a topic of interest
  - Food and diet preferences (e.g. vegan cooking, paleo snacks, gluten-free baking)
  - Kids' activities and logistics (e.g. carpool rotations, camp schedules)

If you are unsure about sensitivity, DROP the memory.

### Examples (combined verdict)

KEEP:
  - "Researches G Loomis NRX fly fishing rods" — GOOD + non-sensitive
  - "Plans outdoor activities like hiking and camping" — GOOD + non-sensitive
  - "Plans trip to Belize, researching accommodation" — GOOD + non-sensitive
  - "Follows NFL fantasy football" — GOOD + non-sensitive
  - "Seeks vegan and vegetarian restaurants" — GOOD + non-sensitive
  - "Consumes news from BBC and Yahoo" — GOOD + non-sensitive
  - "Uses Lichess to drill chess openings" — GOOD (tool tied to a hobby) + non-sensitive
  - "Tracks marathon training splits in Strava" — GOOD (tool tied to a hobby) + non-sensitive
  - "Organizes D&D campaign notes in Obsidian" — GOOD (tool tied to a hobby) + non-sensitive
  - "Compares dispatch software for delivery fleets" — GOOD + non-sensitive (professional, not personal finance)
  - "Studies reinsurance treaty structures" — GOOD + non-sensitive (professional, not personal finance)
  - "Checks customs allowances for bringing espresso beans home from Italy" — GOOD + non-sensitive (travel, not immigration status)
  - "Follows EU data privacy legislation" — GOOD + non-sensitive (policy topic, not a legal case)
  - "Plans pescatarian dinner menus" — GOOD + non-sensitive (diet preference, not a condition)

DROP (low quality):
  - "Uses Zoom for virtual meetings" — GENERIC
  - "Manages email communications for work" — GENERIC
  - "Interacted with Starbucks website" — GENERIC
  - "Tracks package deliveries" — GENERIC

DROP (sensitive):
  - "Researches treatment about arthritis" — medical
  - "Searches about pregnancy tests online" — medical
  - "Pediatrician in San Francisco" — medical
  - "Researches the effects of anxiety on sleep" — medical (mental health)
  - "Reads research on how loneliness affects emotional health" — medical (mental health, even as a general topic)
  - "Researches grief support resources for hospice staff" — medical (mental health, even in a job context)
  - "Tracks mortgage refinance rates" — finance
  - "Negotiates debt settlement with bank" — finance
  - "Prepares documents for divorce hearing" — legal
  - "Applies for work visa extension" — legal (immigration status)
  - "Political leaning towards a party" — politics
  - "Research about ethnicity demographics in a city" — demographics
  - "Marie, female from Ohio looking for rental apartments" — PII

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
