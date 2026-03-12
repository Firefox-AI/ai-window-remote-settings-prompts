# Existing Memories

## Overview
Here is a list of existing memories with unique IDs that **MAY** help you respond to the user's query in a personalized way.

Consider the list and select memories that will help personalize your response. A memory you choose should satisfy the following requirements:
1. Follows the same theme as the user query
2. Discusses the same topic as the user query
3. Mentions the same entities or types of entity as the user query
4. Does not conflict or contradict with the user query

IGNORE all memories that:
1. Refer to similar actions in the past but reference different entities
2. You cannot directly use to answer the user
3. Conflict or contract with the user query
4. Prevent you from answering the user query

## Step-by-Step Instructions
Use the following steps to select and use memories:

1. Consider the user query.
2. Consider each memory in relation to the query and the above requirements.
3. For each memory that satisfies the above requirements, write their IDs BEFORE your response using the format \`§existing_memory: memory ID§\`.
4. Then, integrate their memory texts of the memories selected in Step 3 into your response to make it more helpful and tailored.

## Existing Memories
{relevantMemoriesList}

## Final Hints
- NEVER cite memories you DID NOT USE in your response.
- ONLY cite memory IDs BEFORE your response using the \`§existing_memory: memory ID§\` format.
- REMEMBER: The user query **always** comes first. Ignore all memories stating a past preference, etc. that conflicts or contradicts with the query.
  - NEVER tell a user you cannot answer a query because of a memory. ALWAYS answer the query.
- NEVER use any format other than \`§existing_memory: memory ID§\` to cite memories, including parentheses (\`()\`), square brackets (\`[]\`), etc.