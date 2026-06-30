# Mozilla's Privacy stance

### What are the risks of AI assistants?
AI assistants powered by large language models (LLMs) can behave in unexpected ways. Some common risks include:

1. Open-ended interactions
Users may intentionally or unintentionally request harmful content. This can lead to risks such as physical harm, illegal activity, or financial harm. 

2. Unintended harmful responses
Because LLMs are probabilistic, harmful outcomes cannot be completely prevented, even with safeguards in place. 

3. Incorrect information (hallucinations)
AI systems may generate false or misleading information. 

Mozilla recognizes these risks and works to reduce them while being transparent about the limitations of this technology.


### How Mozilla reduces these risks
Mozilla takes several steps when selecting and operating AI models for Smart Window:

1. Safety evaluations
Models are tested using prompts designed to trigger harmful responses. Results are evaluated based on how often models refuse unsafe requests. 

2. Assistant safeguards
System instructions guide the assistant to avoid harmful content. 

3. Sensitive topic handling
For financial, medical, and legal topics, the assistant provides disclaimers encouraging users to seek professional advice. 

4. How your data is protected
Smart Window includes privacy protections designed to limit exposure of user data:

    Mozilla proxy - Requests are routed through a Mozilla proxy server before reaching AI services. This means:
        The AI service does not see a unique identifier of your Firefox browser or computer
        The AI service does not see your IP address
        The AI service cannot directly identify you or your location 

    No data collection by default
        Conversations will never be collected or stored for training or human review unless you opt in. 

5. Security protections
Smart Window includes protections against emerging risks such as prompt injection attacks. These attacks attempt to hide malicious instructions in web content.
Mozilla addresses these risks by:

    Reducing where prompt injections can occur (for example, limiting the length of tab titles sent to the assistant)
    Labeling conversation state when interacting with untrusted content or private data, so we know when to restrict certain actions the AI has access to, to reduce risk
    Using techniques to distinguish between instructions and data 

6. Ongoing improvements
Security and safety in AI systems continue to evolve. Mozilla:

    Updates protections as new risks are discovered
    Develops new mitigations
    Shares approaches to support transparency and the broader open source community 