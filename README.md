# Codex Model Switchboard

[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111827?style=flat-square)](./SKILL.md)
[![Model Switchboard](https://img.shields.io/badge/Model-Switchboard-0ea5e9?style=flat-square)](./references/provider-notes.md)
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

- Do not commit API keys, bearer tokens, or local provider config files.
- Keep VSCode/App Codex separate unless you explicitly want shared history.
- Back up Codex homes before merging or rewriting provider metadata.
- Do not name a custom provider `openai`; Codex reserves built-in provider IDs.
