# Firefox AI Window Remote Settings Prompts

This repository manages system prompts and generation configurations for Firefox's AI Window features using Remote Settings.

## Repository & File Structure

```
ai-window-remote-settings-prompts/
└── prompts/
    ├── <feature_1>/
        ├── <model_key_1>.md
        ├── <model_key_1>.json
        ...
    ├── <feature_2>/
        ├── <model_key_1>.md
        ├── <model_key_1>.json
        ...
    ...
```

Prompts are organized using the pattern: `prompts/<feature>/<model_key>.{json,md}`.

Each prompt option consists of two files:
- **`.json` file**: contains `metadata` and generation `config`
- **`.md` file**: contains the actual system prompt text in markdown format

### Example: Chat Feature

```
prompts/chat/
  ├── qwen3-235B-A22.json
  ├── qwen3-235B-A22.md
  ├── gemini2.5-flash-lite.json
  ├── gemini2.5-flash-lite.md
  ...
...
```

```json
// qwen3-235B-A22.json
{
  "metadata": {
    "feature": "chat",
    "version": "1.0",
    "model_key": "qwen3-235B-A22",
    "is_default": true,
    "last_updated": "2025-01-15"
  },
  "config": {
    "temperature": 1.0,
    "top_p": 0.001
  }
}
```
