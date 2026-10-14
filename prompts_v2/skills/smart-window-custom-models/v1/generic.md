# Custom Models in Smart Window (Bring Your Own Endpoint)

Smart Window lets power users connect their own AI model instead of using the three built-in options (Fast, Flexible, Personal). This is useful for users who want more control, prefer a specific provider, or want to run a model locally on their device.

## Important caveats — share these upfront

- **Trust and Safety protections do not apply.** The T&S evaluations Mozilla runs on built-in models are not applied to custom endpoints. Users take on the risk themselves.
- **Smart Window may not work as expected** with a custom model.
- **The system prompt cannot be modified.** Smart Window's system prompt is fixed and applies regardless of which model is connected.
- This feature is intended for users familiar with AI APIs, model endpoints, and tools like Ollama or OpenRouter.

## How to connect a custom model (general steps)

In Firefox:
1. Open **Settings**
2. Go to **AI Controls** > **Smart Window Settings** > **Assistant model**
3. Select **Custom: Use your own LLM**
4. Fill in the three fields:
   - **Model name** — the model identifier from your provider
   - **Model endpoint** — the API endpoint URL
   - **API key or auth token** — if required by the provider (leave blank if not needed)
5. Click **Save**
6. Open a Smart Window and start using the assistant

---

## Option 1: Remote model via OpenRouter

OpenRouter is a platform that provides access to many models through a single API, including free options.

1. Create an account at **https://openrouter.ai/** if you don't have one
2. Generate an API key in OpenRouter and save it somewhere secure
   - OpenRouter API keys begin with `sk-or-v1-`
3. Open the OpenRouter models page and choose a model
   - Note its **model ID** (e.g., `z-ai/glm-4.5-air:free`)
4. In Firefox, open **Settings** > **AI Controls** > **Smart Window Settings** > **Assistant model**
5. Select **Custom: Use your own LLM**
6. Fill in the fields:
   - **Model name:** paste the OpenRouter model ID from step 3
   - **Model endpoint:** `https://openrouter.ai/api/v1`
   - **API key:** paste your OpenRouter API key from step 2
7. Click **Save**

**Tip:** Free models are available on OpenRouter — search for "free" on the models page to filter them.

---

## Option 2: Local model via Lemonade Server

Lemonade Server runs models locally on the user's device.

**Requirements:** Version 10.2.0 or newer.

1. Download and install Lemonade Server from **https://lemonade-server.ai/**
2. Run Lemonade Server and download a model using the app instructions
3. In a terminal, set a larger context size:
   ```
   lemonade config set ctx_size=8192
   ```
4. Reload the model from the UI, or run `lemonade unload` (it will reload with new settings on the next request)
5. In Firefox, open **Settings** > **AI Controls** > **Smart Window Settings** > **Assistant model**
6. Select **Custom: Use your own LLM**
7. Fill in the fields:
   - **Model name:** enter the model name from step 2 (e.g., `SmolLM3-3B-GGUF`)
   - **Model endpoint:** `http://localhost:13305/api/v1`
   - **API key:** not required — leave blank
8. Click **Save**

---

## Option 3: Local model via Ollama

Ollama runs open-weight models locally on the user's device.

1. Download and install Ollama from **https://ollama.com/download**
2. Run Ollama and follow the on-site instructions to download a local model of your choice
3. In Firefox, open **Settings** > **AI Controls** > **Smart Window Settings** > **Assistant model**
4. Select **Custom: Use your own LLM**
5. Fill in the fields:
   - **Model name:** enter the model name from step 2 (e.g., `qwen3.5:4b`)
   - **Model endpoint:** `http://localhost:11434/v1`
   - **API key:** not required — leave blank
6. Click **Save**

---

## Troubleshooting tips

- If the assistant isn't responding after saving, double-check the model name and endpoint URL — small typos will cause failures
- For local models (Lemonade, Ollama), make sure the local server is running before opening Smart Window
- If the model seems to ignore instructions or behave unexpectedly, this is expected — custom models may not be optimized for Smart Window's use cases
- To switch back to a built-in model, return to **Settings** > **AI Controls** > **Smart Window Settings** > **Assistant model** and select Fast, Flexible, or Personalized
