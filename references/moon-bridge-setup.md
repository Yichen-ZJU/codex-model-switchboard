# Moon Bridge + DeepSeek Setup

This reference is for first-time setup. The goal is to make Codex CLI talk to DeepSeek through Moon Bridge while preserving the official OpenAI provider and enabling shared `/resume` history.

## 1. Requirements

- Node.js 18+
- Go 1.25+
- Codex CLI

```bash
npm install -g @openai/codex
codex --version
go version
```

## 2. Get A DeepSeek Key

Create a key from the DeepSeek platform. Store it outside git, for example in an environment variable or a local key file with `chmod 600`.

Never commit API keys.

## 3. Clone Moon Bridge

```bash
git clone https://github.com/ZhiYi-R/moon-bridge.git
cd moon-bridge
```

## 4. Create A Minimal DeepSeek Config

Create `config.yml`:

```yaml
mode: "Transform"

server:
  addr: "127.0.0.1:38440"

models:
  deepseek-v4-pro:
    context_window: 1000000
    max_output_tokens: 384000
    default_reasoning_level: "high"
    supported_reasoning_levels:
      - effort: "high"
        description: "High reasoning effort"
      - effort: "xhigh"
        description: "Extra high reasoning effort"
    supports_reasoning_summaries: true
    default_reasoning_summary: "auto"
    extensions:
      deepseek_v4:
        enabled: true
  deepseek-v4-flash:
    context_window: 1000000
    max_output_tokens: 384000
    default_reasoning_level: "high"
    supported_reasoning_levels:
      - effort: "high"
        description: "High reasoning effort"
      - effort: "xhigh"
        description: "Extra high reasoning effort"
    supports_reasoning_summaries: true
    default_reasoning_summary: "auto"
    extensions:
      deepseek_v4:
        enabled: true

providers:
  deepseek:
    base_url: "https://api.deepseek.com/anthropic"
    api_key: "replace-with-deepseek-key"
    offers:
      - model: deepseek-v4-pro
      - model: deepseek-v4-flash

routes:
  moonbridge:
    model: deepseek-v4-pro
    provider: deepseek

defaults:
  model: moonbridge
  max_tokens: 65536
```

## 5. Start Moon Bridge

```bash
go run ./cmd/moonbridge --config config.yml
```

Moon Bridge listens at:

```text
http://127.0.0.1:38440/v1/responses
```

## 6. Generate Codex Config Without Breaking OpenAI

Moon Bridge can print a Codex config and model catalog:

```bash
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME_DIR"
cp "$CODEX_HOME_DIR/config.toml" "$CODEX_HOME_DIR/config.toml.bak" 2>/dev/null || true

MODEL="$(go run ./cmd/moonbridge --config config.yml --print-codex-model)"
go run ./cmd/moonbridge \
  --config config.yml \
  --print-codex-config "$MODEL" \
  --codex-base-url "http://127.0.0.1:38440/v1" \
  --codex-home "$CODEX_HOME_DIR" \
  > "$CODEX_HOME_DIR/config.toml"
```

For this skill, prefer a safer variant:

- Keep official OpenAI as the default provider in `config.toml`.
- Add Moon Bridge under `[model_providers.moonbridge]`.
- Store Moon Bridge's generated model catalog as `moonbridge_models_catalog.json`.
- Pass that catalog only when launching the Moon Bridge provider.

This prevents the generated catalog from hiding official GPT models.

## 7. Launch Codex Through Moon Bridge

```bash
CODEX_HOME="$CODEX_HOME_DIR" codex \
  -m moonbridge \
  -c 'model_provider="moonbridge"' \
  -c "model_catalog_json=\"${CODEX_HOME_DIR}/moonbridge_models_catalog.json\""
```

Before launch, run `scripts/sync_resume_provider.py` so `/resume` shows the same CLI sessions under Moon Bridge:

```bash
python /path/to/codex-model-switchboard/scripts/sync_resume_provider.py \
  --codex-home "$CODEX_HOME_DIR" \
  --provider moonbridge \
  --model moonbridge
```

## 8. Verify

```bash
curl http://127.0.0.1:38440/v1/models
```

```bash
curl http://127.0.0.1:38440/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "moonbridge",
    "input": "Say hello in one short sentence.",
    "max_output_tokens": 1024
  }'
```

## Troubleshooting

- `connection refused`: Moon Bridge is not running, or `server.addr` uses another port.
- Codex cannot see the model: regenerate or pass the Moon Bridge model catalog at launch.
- `field provider not found`: the config uses an old schema. Current Moon Bridge configs use top-level `models`, `providers`, `routes`, and `defaults`.
- `model_providers contains reserved built-in provider IDs: openai`: do not define a custom `[model_providers.openai]`; use `moonbridge`, `mimo`, or another custom ID.
- `401`: check the DeepSeek API key.
- `402`: check DeepSeek account balance.
- `codex_apps` MCP failed to start: Codex could not reach the ChatGPT Apps MCP endpoint. This is separate from the Moon Bridge/DeepSeek model route and does not usually block normal Codex CLI chat.
