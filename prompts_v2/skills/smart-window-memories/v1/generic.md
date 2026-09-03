# Smart Window Memories

Memories are short summaries Firefox creates by learning from a user's activity. They help the built-in assistant give more personalized responses over time. Memories are optional and stored locally on the device.

**Important:** Firefox never uses activity from Private Windows to create memories.

## What memories are

Memories are brief, human-readable summaries of patterns in the user's activity — things like topics they research, preferences they express, or habits they have. They are not raw browsing data. Examples of what a memory might look like:

- "Researches local hiking trails"
- "Follows WNBA league standings"
- "Edits emails to sound professional"
- "Plans trips to Austin"
- "Prefers vegan recipes and cuisine"

Filters are in place to prevent memories from being created on sensitive topics like health, finance, and legal matters.

## How memories are created

Memories are created from two possible sources, which users can enable or disable independently:

- **Browsing activity** in Classic and Smart Windows
- **Chat activity** in Smart Window

**First-time setup:** When a user first uses Smart Window with memories enabled, Firefox may create initial memories using up to 60 days of browsing history or 3,000 items — whichever limit is reached first.

**Ongoing updates:** Memories update automatically in the background when meaningful new activity is detected. Updates may happen when:
- The user visits at least 30 new pages since the last update
- There are at least 10 visits within 60 days and a noticeable change in browsing activity (e.g., exploring new topics)
- The user sends at least 10 new messages in Smart Window

If Smart Window is closed, memory updates pause. When the user returns, any browsing activity during that time may be used once Smart Window is active again.

## How memories are used

When the user chats with the assistant, it queries their memories to see if anything relevant could personalize the response. For example, a user with a memory like "Prefers vegan recipes and cuisine" who asks "recommend a recipe for dinner" will likely get vegan suggestions rather than general ones.

When a response uses memories:
- A **memories icon** appears below the response
- Selecting the icon shows which memories were used
- The user can delete any memory from that pop-up if it seems wrong
- Selecting **Retry without memories** generates a non-personalized response

## Turn off memories for a single chat session

To disable memories for one conversation without changing settings:

1. In the assistant entry box, find the memories icon
2. Turn the memories toggle off for that chat
3. Continue the conversation

Note: This stops memories from being *used* in that chat, but new memories may still be *created* from the conversation.

## How to manage memories

### View and delete memories

1. Open **Settings**
2. Go to **AI controls**
3. Select **Smart Window**
4. Select **Manage memories**

From there, the user can:
- Delete individual memories using the trash icon next to each one
- Delete all memories at once using the **Delete all** button

### Change what activity memories are based on

1. Open **Settings**
2. Go to **AI controls**
3. Select **Smart Window**
4. Under **Memories**, choose which activity sources to learn from

### Stop new memories from being created

To stop all new memories from being created:

1. Open **Settings**
2. Select **AI controls**
3. Select **Smart Window settings**
4. Under **Memories**, uncheck both:
   - **Learn from browsing activity**
   - **Learn from chat activity**

**Important nuance:** Turning off learning only stops *new* memories from being created. Existing memories will still be used to personalize responses by default. If the user wants no personalization at all, they also need to delete their existing memories from Manage memories.

## Privacy and how memories are processed

- To create memories, browsing and chat history are sent to a Mozilla server for processing. Mozilla does not retain this data after processing.
- Memories are returned and stored **locally on the user's device** — only the user can see them.
- Mozilla does not sell this data to advertisers.
- Memories are not synced across devices.

## Common questions

**If I delete my history and chats, are my memories deleted too?**
No. Memories are stored separately. Deleting browsing history or chat history does not delete memories. To remove memories, go to Settings > AI controls > Smart Window > Manage memories.

**Can I ask for specific memories to be created?**
No. The assistant cannot create a memory on request. It may remember things within a single chat, but that does not persist as a permanent memory.

**Are memories synced across devices?**
No. Memories are stored locally and cannot be synced.

**Are memories used even if I turn off learning?**
Yes, by default. Turning off learning stops new memories from being created, but existing memories are still used unless they are also deleted.
