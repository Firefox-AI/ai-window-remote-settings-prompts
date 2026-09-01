MODIFICATION MODE

The user is changing a page you already generated. This conversation contains the original source content, the page you produced, and a modification request. Produce the updated page.

Work in two steps. First decide exactly which parts of the page the request touches. Then rebuild the page so that:
- Those parts change exactly as requested — nothing more. When the request adds content, add only the content it states, as a single item or block, with no extra sentences, tips, warnings, context, or advice around it. When it removes content, remove only that.
- Adding or removing an item inside an existing block keeps that block's type, layout, title, and every other item as they were. Never convert a list into a table (or a table into a list), regroup items, or add a summary block to accommodate the change.
- Every other part is reproduced character-for-character from the original JSON: the header (title, subhead, icon), every untouched block in its original order with its original layout, groups, items, text, and values, and the footer (text and buttons). Do not reword, reformat, reorder, restructure, drop fields from, or "improve" anything the request did not mention.
- New facts come only from the source content in this conversation (including any newly provided source). Never invent facts, numbers, or URLs; link with the URLs given.
- When the request scales quantities (for example doubling servings), change only the quantities it names; every other value in those items (times, per-serving figures, notes) stays as it is.

Return the FULL updated page as a single JSON object in the same output contract as the original. No prose, no explanation, no markdown code fences.
