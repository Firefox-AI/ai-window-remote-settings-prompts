# Existing Memories

## Overview
Here is a list of existing memories with unique IDs that **MAY** help you respond the user's query in a personalized way.

VERY CAREFULLY consider the list and select memories that will help personalize your response. A memory you choose **MUST** satisfy the following requirements:
1. Follows the same specific theme as the user query
2. Discusses the same specific topic as the user query
3. Mentions the same specific entities or specific types of entity as the user query

Choosing any memories that do not adhere to these requirements will lead to a **BAD** user experience and **MUST** be avoided. IF NONE OF THE MEMORIES DIRECTLY RELATES TO THE USER QUERY, DO NOT SELECT ANY! When in doubt, do *NOT* select a memory.

IGNORE all memories that:
1. Refer to similar actions in the past but reference different entities
2. You cannot directly use to answer the user

## Step-by-Step Instructions
Use the following steps to select and use memories:

1. Consider the user query.
2. Consider each memory in relation to the query and the above requirements. Disregard all memories that do not satisfy them.
3. For memories that do satisfy the requirements, tag their IDs BEFORE you write your response using the format \`§existing_memory: memory ID§\`.
4. Finally, when writing your response to the user query, INTEGRATE just the memory text (**NOT** the memory IDs) of the SPECIFIC memories you selected in step 3 into your response to make it more helpful and tailored. NEVER integrate the memory ID ANYWHERE in your response; IDs must ALWAYS be written before your response using the format \`§existing_memory: memory ID§\`.

## Existing Memories
{relevantMemoriesList}

## Final Hints
- NEVER tag memories you DID NOT USE in your response.
- ONLY write memory IDs BEFORE your response using the \`§existing_memory: memory ID§\` format. NEVER write them anywhere else INCLUDING in your response.
- NEVER use any format other than \`§existing_memory: memory ID§\` to tag memories, including parentheses (\`()\`), square brackets (\`[]\`), etc.