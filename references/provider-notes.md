# Provider Notes

## Reserved Provider IDs

Codex reserves built-in provider IDs such as `openai`. Custom providers must use another ID:

```toml
[model_providers.moonbridge]
name = "Moon Bridge"
base_url = "http://127.0.0.1:38440/v1"
wire_api = "responses"
```

If a config contains `[model_providers.openai]`, Codex fails with:

```text
model_providers contains reserved built-in provider IDs: `openai`
```

## Model Catalog Placement

For bridge providers, keep generated catalog metadata separate from the official Codex model catalog:

```bash
/path/to/codex-homes/cli/moonbridge_models_catalog.json
```

Prefer launch-time override:

```bash
codex -m moonbridge \
  -c 'model_provider="moonbridge"' \
  -c 'model_catalog_json="/path/to/codex-homes/cli/moonbridge_models_catalog.json"'
```

This avoids breaking the official OpenAI model list.

## Shared CLI Home Pattern

Use one terminal-only home:

```bash
export CODEX_SHARED_CLI_HOME=/path/to/codex-homes/cli
```

Then force official GPT and third-party launches to use it:

```bash
CODEX_HOME="$CODEX_SHARED_CLI_HOME" codex
CODEX_HOME="$CODEX_SHARED_CLI_HOME" codex -m moonbridge -c 'model_provider="moonbridge"'
```

Do not set VSCode/App Codex to this home unless the user explicitly asks for App history sharing.

## Resume Metadata

Codex may rebuild `threads` rows from rollout transcript metadata. For provider switching, update both:

- `state_*.sqlite`
- `sessions/**/rollout-*.jsonl`

Use `scripts/sync_resume_provider.py` before launching the selected provider.

## Moon Bridge Provider Examples

For full first-time installation and verification, see `moon-bridge-setup.md`.

DeepSeek V4 is typically exposed through a Moon Bridge route using the Responses-compatible interface:

```yaml
providers:
  deepseek:
    base_url: "https://api.deepseek.com/anthropic"
    api_key: "replace-with-key"
    offers:
      - model: deepseek-v4-pro

routes:
  moonbridge:
    model: deepseek-v4-pro
    provider: deepseek
```

Xiaomi MiMo v2.5 Pro has been validated through an OpenAI Chat Completions-compatible endpoint:

```yaml
providers:
  mimo:
    base_url: "https://token-plan-cn.xiaomimimo.com/v1"
    api_key: "replace-with-token"
    protocol: "openai-chat"
    offers:
      - model: mimo-v2.5-pro

routes:
  mimo:
    model: mimo-v2.5-pro
    provider: mimo
```

MiniMax-M3 has also been validated through an OpenAI Chat Completions-compatible endpoint:

```yaml
providers:
  minimax:
    base_url: "https://api.minimaxi.com/v1"
    api_key: "replace-with-token"
    protocol: "openai-chat"
    offers:
      - model: MiniMax-M3

routes:
  minimax:
    model: MiniMax-M3
    provider: minimax
```

MiniMax-M3 responses may include `<think>...</think>` text in the assistant output. If a downstream UI needs the final answer only, strip that block after generation.

The same pattern should apply to GLM, Qwen, Kimi, and internal APIs when they expose an adapter protocol supported by the bridge layer.
