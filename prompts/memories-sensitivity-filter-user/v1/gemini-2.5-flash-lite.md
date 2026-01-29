You are an expert at identifying sensitive statements and content.

Examine the following list of statements and filter out any that contain sensitive information or content.
Sensitive information includes, but is not limited to:

- Medical/Health: diagnoses, symptoms, treatments, conditions, mental health, pregnancy, fertility, contraception.
- Finance: income/salary/compensation, bank/credit card details, credit score, loans/mortgage, taxes/benefits, debt/collections, investments/brokerage.
- Legal: lawsuits, settlements, subpoenas/warrants, arrests/convictions, immigration status/visas/asylum, divorce/custody, NDAs.
- Politics/Demographics/PII: political leaning/affiliation, religion, race/ethnicity, gender/sexual orientation, addresses/phones/emails/IDs.

Below are exemplars of sensitive statements:
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

If all statements are not sensitive, simply return them all.

Here are the statements to analyze:
{memoriesList}

Return ONLY JSON per the schema below.
```json
{
  "non_sensitive_memories": [
    "<memory_statement_1>",
    "<memory_statement_2>",
    ...
  ]
}
```
