You are an expert at identifying duplicate statements.

Examine the following list of statements and find the unique ones. If you identify a set of statements that express the same general idea, pick the most general one from the set as the "main memory" and mark the rest as duplicates of it.

There are 2 lists of statements: Existing Statements and New Statements. If you find a duplicate between the 2, **ALWAYS** pick the Existing Statement as the "main memory".

If all statements are unique, simply return them all.

## Existing Statements:
{existingMemoriesList}

## New Statements:
{newMemoriesList}

Return ONLY JSON per the schema below.
```json
{
  "unique_memories": [
    {
      "main_memory": "<the main unique memory statement>",
      "duplicates": [
        "<duplicate_statement_1>",
        "<duplicate_statement_2>",
        ...
      ]
    },
    ...
  ]
}
```
