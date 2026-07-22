# Smart Window Trust and Safety

Smart Window uses large language models (LLMs) to help users with browsing tasks. Like all AI-based products, it carries inherent risks. Mozilla works to reduce those risks and is transparent about the limitations of this technology.

## Risks of AI assistants

When answering questions about AI risks, be honest about what LLMs can and cannot guarantee:

**Open-ended interactions**
Users may — intentionally or not — request content that creates real-world risks (physical or financial harm, illegal activity). The assistant is designed to decline such requests, but not every case can be caught.

**Unintended harmful responses**
Because LLMs are probabilistic, harmful outputs cannot be completely prevented even with safeguards in place.

**Incorrect information (hallucinations)**
AI systems may generate false or misleading information presented confidently. Users should verify important information from authoritative sources.

Mozilla recognizes these risks and works to reduce them while being transparent about the limitations.

## How Mozilla reduces risks

**Safety evaluations**
Before any model is made available in Smart Window, Mozilla tests it using prompts designed to trigger harmful responses. Models are evaluated on how reliably they refuse unsafe requests.

**Assistant safeguards**
System instructions guide the assistant to avoid harmful content.

**Sensitive topic handling**
For questions involving financial, medical, or legal topics, the assistant provides disclaimers encouraging users to seek professional advice. 

**Ongoing improvements**
Mozilla updates protections as new risks are discovered, develops new mitigations, and shares its approaches to support transparency and the open source community.

## How user data is protected

**Mozilla proxy**
All requests are routed through a Mozilla proxy server before reaching AI services. This means:
- The AI service does not see the user's IP address
- The AI service does not see a unique identifier of the user's Firefox browser or computer
- The AI service cannot directly identify the user or their location

**No data collection by default**
Conversations are not collected or stored for training or human review.

**No model training on user data**
None of the models used by Smart Window are trained on user data.

**What Smart Window can access:**
- The page the user is currently viewing
- Open tabs the user explicitly references (via @ or the plus button)
- Browsing history the user explicitly asks about (from Classic and Smart Windows)

**What Smart Window cannot access:**
- Activity or data from Private Windows
- Passwords
- Payment information
- Unread emails
- Files on the user's device

## Security protections

Smart Window includes measures to reduce the risk of **prompt injection attacks** — attempts to hide malicious instructions inside web content (for example, in a page the user is reading).

Mozilla addresses this by:
- Limiting the length of tab titles and other content sent to the assistant, reducing the attack surface
- Labeling conversation state when interacting with untrusted content or private data, to restrict what the AI can do in those contexts
- Using techniques to distinguish between instructions and data

## Custom models and safety

Trust and Safety protections apply only to the three built-in models (Fast, Flexible, Personalized). If a user is using a **custom/BYO model endpoint**, these protections do not apply. Users who choose a custom model do so at their own risk.

## How to report a bad response

If the user gets a response that seems harmful, wrong, or inappropriate, they can report it using the feedback option in the Smart Window interface.
