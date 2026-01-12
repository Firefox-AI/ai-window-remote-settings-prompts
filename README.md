# Firefox AI Window Remote Settings Prompts

This repository stores and manages system prompts and generation configurations for Firefox's AI Window features using Remote Settings.

Data in this repo should be viewed as the main source of truth.

# Repository & File Structure

## Overall

```
ai-window-remote-settings-prompts/
└── prompts/
    ├── <major_version_number>
        ├── <feature_1>/
            ├── <model_1>.md
            ├── <model_1>.json
            ...
        ├── <feature_2>/
            ├── <model_1>.md
            ├── <model_1>.json
            ...
        ...
```

Prompts are organized using the pattern: `prompts/<feature>/<model>.{json,md}`.

Each prompt option consists of two files:
- **`.json` file**: contains `metadata` and generation `parameters`
- **`.md` file**: contains the actual system prompt text in markdown format

### Example: Chat Feature

Folder:
```
prompts/
  chat/
    v1/
      ├── gemini2.5-flash-lite.json
      ├── gemini2.5-flash-lite.md
      ├── gpt-oss-120b.json
      ├── gpt-oss-120b.md
      ├── qwen3-235b-a22b-instruct-2507-maas.json
      ├── qwen3-235b-a22b-instruct-2507-maas.md
    ...
  ...
```

<model_name.json>:
```json
{
  "feature": "chat",
  "version": "1.0",  # <major_version>.<minor_minor>
  "model": "qwen3-235b-a22b-instruct-2507-maas",
  "is_default": true,
  "parameters": {
    "temperature": 1.0
  },
}
```
<model_name.md>:
```
You are a helpful assistant ...
```

# Remote Settings Update Principal

This section lists important rules to follow when updating PROD remote settings to ensure the correctness of the data in the remote.

## Terminology

1. **Major version**: Increment the major version when making significant changes to prompt content or functionality that would break compatibility with the current version or require code changes.
2. **Minor version**: Increment the minor version for minor prompt tuning and parameter updates that don't significantly impact the prompt's purpose or require code changes.

## Rules

1. Remote settings must contain the **LATEST** minor version for **EACH** combination of major version, feature, and model.
2. When incrementing a new major version, **create** a new version directory along with a new record (e.g., v1.x -> v2.0 creates a new directory and record while keeping v1.x). This is necessary to maintain support for previous versions. All breaking features (e.g. the addition of new tools) should get a new major version number.
3. When incrementing a new minor version, **edit** the existing record (e.g., v1.0 -> v1.1 updates the same record).
4. Only keep the latest minor version for each major version to avoid accumulating unnecessary historical data and reducing network transfer overhead.
5. For major version increments, first update remote settings with the new major version, then update the local config's major version reference and fallback prompts in MC to match.
6. For each feature & major version combination, only one model should be set as default (`is_default === true`).

# Prompt Owners

Please refer to the following table for the owners of each prompt and config.

| Feature | Owners |
|---------|-------|
| chat | Tom Zhang, Mohan Zhang |
| conversation-suggestions-assistant-limitations | Molly Shillabeer |
| conversation-suggestions-followup | Molly Shillabeer |
| conversation-suggestions-memories | Molly Shillabeer |
| conversation-suggestions-sidebar-starter | Molly Shillabeer |
| title-generation | Mohan Zhang |
