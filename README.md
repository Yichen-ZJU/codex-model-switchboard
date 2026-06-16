# Codex Model Switchboard

[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111827?style=flat-square)](./SKILL.md)
[![Model Switchboard](https://img.shields.io/badge/Model-Switchboard-0ea5e9?style=flat-square)](./references/provider-notes.md)
[![Moon Bridge](https://img.shields.io/badge/Moon%20Bridge-DeepSeek-6366f1?style=flat-square)](./references/moon-bridge-setup.md)
[![Shared Resume](https://img.shields.io/badge/%2Fresume-shared-22c55e?style=flat-square)](./scripts/sync_resume_provider.py)

[中文说明](./README.zh-CN.md)

A Codex skill for switching between official OpenAI Codex models and third-party model providers through bridge/proxy layers while keeping terminal `/resume` history shared across providers.


## Tested Providers

- Official OpenAI/GPT Codex provider.
- DeepSeek V4 through Moon Bridge.
- Xiaomi MiMo v2.5 Pro through Moon Bridge using `protocol: "openai-chat"`.

Other providers such as GLM, Qwen, Kimi, or internal OpenAI-compatible APIs should follow the same pattern when they expose a supported protocol (`openai-chat`, `openai-response`, `anthropic`, or another adapter supported by your bridge layer).

## Why This Exists

DeepSeek's official recommendation for Codex CLI users is to connect through Moon Bridge. That guide gets you a working DeepSeek model inside Codex, which is half the battle. The other half is what happens when you switch back to the official GPT provider: your DeepSeek conversations vanish from `/resume`. Switch again and your GPT conversations are gone. Each provider sees only its own history, and manually copying `history.jsonl` does not fix it.

This is not a DeepSeek or Moon Bridge bug. It is a deeper problem with how Codex resolves resumable history. Codex `/resume` is not backed only by `history.jsonl`.

It also depends on:

- `state_*.sqlite`, especially the `threads` table.
- The first `session_meta` line in `sessions/**/rollout-*.jsonl`.

Codex can rebuild SQLite thread metadata from rollout transcripts. Updating only `history.jsonl` or only SQLite is not enough: Codex will overwrite your changes on the next launch. To make the same terminal history visible under different providers, both SQLite and rollout `session_meta.model_provider` must be synchronized.

This skill automates that synchronization. The result: you can switch between OpenAI GPT and any bridge-backed provider and pick up the same conversation right where you left off, with `/resume` listing all terminal sessions regardless of which provider they were created under. VSCode and App conversations stay in their own silo by default.

The mechanism is provider-agnostic. It was first built for DeepSeek via Moon Bridge and later validated with Xiaomi MiMo v2.5 Pro. Any provider reachable through a Codex-compatible adapter (Moon Bridge, LiteLLM, OpenAI-compatible proxy) should follow the same pattern.

## From Zero To DeepSeek In Codex

If you are starting from a clean machine, follow the complete Moon Bridge setup reference:

[Moon Bridge + DeepSeek Setup](./references/moon-bridge-setup.md)

It covers:

- installing Node.js, Go, and Codex CLI
- cloning Moon Bridge
- creating the current top-level `models` / `providers` / `routes` config
- generating Codex provider metadata and model catalog
- launching Codex through Moon Bridge
- verifying `/v1/models` and `/v1/responses`
- common failures such as reserved `openai` provider IDs and stale model catalogs

This repository adds the missing operational layer on top of that setup: safe provider switching and shared `/resume` history across official GPT and bridge-backed providers.

## What It Provides

- A workflow for using one terminal-only `CODEX_HOME` across multiple providers.
- A provider pattern that does not override Codex's reserved built-in `openai` provider.
- CLI history merging while excluding VSCode/App sessions by default.
- `/resume` repair scripts that sync both SQLite and transcript metadata.
- Provider examples for DeepSeek and MiMo via Moon Bridge.

## Included Scripts

- `scripts/merge_codex_homes.py`: merge CLI history, session files, and thread rows from multiple Codex homes.
- `scripts/sync_resume_provider.py`: switch resumable history visibility between providers such as `openai/gpt-5.5`, `moonbridge/moonbridge`, or `mimo/mimo-v2.5-pro`.

## Install

Copy or clone this repository into a Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/Yichen-ZJU/codex-model-switchboard.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/codex-model-switchboard"
```

Then ask Codex:

```text
Use $codex-model-switchboard to configure Codex CLI model switching with shared /resume history.
```

## Safety Notes

- Keep VSCode/App Codex separate unless you explicitly want shared history.
- Back up Codex homes before merging or rewriting provider metadata.
- Do not name a custom provider `openai`; Codex reserves built-in provider IDs.

## Troubleshooting Notes

- `codex_apps` MCP failed to start: Codex could not reach the ChatGPT Apps MCP endpoint. If the TUI still shows `model: moonbridge`, Moon Bridge/DeepSeek is running; this warning is usually unrelated to ordinary Codex CLI chat.
- `/resume` shows only one provider's sessions: run `scripts/sync_resume_provider.py` before launching the selected provider.
- Official GPT models disappear after Moon Bridge setup: remove global `model_catalog_json` and pass the Moon Bridge catalog only in the Moon Bridge launch wrapper.

## Credits

- [DeepSeek](https://github.com/deepseek-ai) for the DeepSeek models and Codex/Moon Bridge setup guidance.
- [Moon Bridge](https://github.com/ZhiYi-R/moon-bridge) for the Responses-compatible forwarding layer.
