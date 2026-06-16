---
name: codex-model-switchboard
description: Configure Codex CLI to switch between official OpenAI/GPT models and third-party providers through bridge/proxy layers while sharing terminal /resume history. Use when setting up Moon Bridge, DeepSeek V4, Xiaomi MiMo, GLM, Qwen, Kimi, OpenAI-compatible providers, fallback models for Codex CLI, merging CODEX_HOME histories, fixing /resume showing only one session, or keeping CLI history separate from VSCode/App Codex conversations.
---

# Codex Model Switchboard

## Core Goal

Set up multiple Codex CLI entry points that share one terminal-only `CODEX_HOME`:

- Official Codex path: default `codex` uses OpenAI/GPT.
- Third-party path: a wrapper starts a bridge/proxy provider and runs Codex with that provider/model.
- Every CLI entry point sees the same `/resume` list.
- VSCode/App conversations stay isolated unless the user explicitly points them at the same `CODEX_HOME`.

Validated examples include DeepSeek V4 through Moon Bridge and Xiaomi MiMo v2.5 Pro through Moon Bridge using `protocol: "openai-chat"`. Other OpenAI-compatible or bridge-supported providers should use the same pattern.

## Non-Negotiables

- Do not overwrite the user's main `~/.codex/config.toml` unless explicitly asked.
- Do not print or hard-code API keys in responses, scripts, or committed files.
- Back up `state_*.sqlite`, `history.jsonl`, `session_index.jsonl`, and `sessions/` before migrations.
- Treat `/resume` as a SQLite plus transcript-metadata problem, not only a `history.jsonl` problem.
- Exclude `source='vscode'` rows when merging histories unless the user explicitly wants App/VSCode sharing.
- Do not name a custom provider `openai`; Codex reserves built-in provider IDs.

## Implementation Workflow

For a first-time DeepSeek/Moon Bridge setup, read `references/moon-bridge-setup.md` before editing configs. For an existing Codex/Moon Bridge setup, use the shorter workflow below.

1. Choose a canonical terminal Codex home, for example:

   ```bash
   /path/to/codex-homes/cli
   ```

2. Configure the canonical home so ordinary `codex` still defaults to the official provider:

   ```toml
   model_provider = "openai"
   model = "gpt-5.5"

   [model_providers.moonbridge]
   name = "Moon Bridge"
   base_url = "http://127.0.0.1:38440/v1"
   wire_api = "responses"
   ```

3. Configure bridge/proxy providers under unique provider IDs such as `moonbridge`, `mimo`, `glm`, or `qwen`. If a bridge uses a separate model catalog, store it in the canonical home, but avoid setting it globally unless the official GPT model list still works.

4. Merge existing terminal homes with `scripts/merge_codex_homes.py`.

5. Before launching a provider, run `scripts/sync_resume_provider.py`:

   ```bash
   python scripts/sync_resume_provider.py \
     --codex-home /path/to/codex-homes/cli \
     --provider moonbridge \
     --model moonbridge
   ```

   For another provider such as MiMo:

   ```bash
   python scripts/sync_resume_provider.py \
     --codex-home /path/to/codex-homes/cli \
     --provider mimo \
     --model mimo-v2.5-pro
   ```

## Why `/resume` Often Still Shows One Session

Codex `/resume` is not driven only by `history.jsonl` or `session_index.jsonl`.

It also reads `state_*.sqlite`, especially `threads`, and Codex can rebuild that table from each rollout transcript's first `session_meta` line. If only SQLite is edited, Codex may overwrite the edit on startup.

When making histories mutually visible across providers, update both:

- `state_*.sqlite`: `threads.model_provider`, `threads.model`, `threads.source`, `threads.thread_source`, `threads.has_user_event`, `threads.archived`
- `sessions/**/rollout-*.jsonl`: first line `{"type":"session_meta", "payload": {"model_provider": ...}}`

The bundled `sync_resume_provider.py` handles both.

## Launch Wrapper Pattern

Use wrappers for third-party providers rather than permanently changing the user's default Codex provider:

```bash
CODEX_HOME="$SHARED_CODEX_HOME" codex \
  -m moonbridge \
  -c 'model_provider="moonbridge"' \
  -c "model_catalog_json=\"${SHARED_CODEX_HOME}/moonbridge_models_catalog.json\""
```

For a shell alias/function, sync first:

```bash
codex() {
  python /path/to/skill/scripts/sync_resume_provider.py \
    --codex-home "$CODEX_SHARED_CLI_HOME" \
    --provider openai \
    --model gpt-5.5
  CODEX_HOME="$CODEX_SHARED_CLI_HOME" command codex "$@"
}
```

Moon Bridge provider configs can route any supported upstream protocol. For example, Xiaomi MiMo v2.5 Pro can be exposed with:

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

## Diagnostics

Check which records are visible to the current provider:

```bash
sqlite3 "$CODEX_HOME/state_5.sqlite" \
  "select model_provider, model, source, thread_source, has_user_event, archived, count(*) from threads group by 1,2,3,4,5,6;"
```

Check transcript metadata:

```bash
python scripts/sync_resume_provider.py --codex-home "$CODEX_HOME" --provider moonbridge --model moonbridge --dry-run
```

Validate from the real TUI, not just the database:

```bash
CODEX_HOME="$CODEX_HOME" codex -m moonbridge \
  -c 'model_provider="moonbridge"' \
  -c "model_catalog_json=\"${CODEX_HOME}/moonbridge_models_catalog.json\"" \
  resume --all --include-non-interactive
```

## Bundled Resources

- `scripts/merge_codex_homes.py`: merge CLI history/session/thread records from multiple `CODEX_HOME` directories into one canonical home, excluding VSCode by default.
- `scripts/sync_resume_provider.py`: rewrite both SQLite thread metadata and rollout `session_meta.model_provider` so `/resume` works under the selected provider.
- `references/moon-bridge-setup.md`: first-time Moon Bridge + DeepSeek setup, Codex config generation, validation, and troubleshooting.
- `references/provider-notes.md`: compact notes for Moon Bridge, Codex config patterns, and provider examples.
