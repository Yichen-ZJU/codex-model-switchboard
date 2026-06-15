# Codex Model Switchboard：多模型切换与共享记忆

[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111827?style=flat-square)](./SKILL.md)
[![Model Switchboard](https://img.shields.io/badge/Model-Switchboard-0ea5e9?style=flat-square)](./references/provider-notes.md)
[![共享 /resume](https://img.shields.io/badge/%2Fresume-%E5%85%B1%E4%BA%AB-22c55e?style=flat-square)](./scripts/sync_resume_provider.py)

一个用于 Codex CLI 的多模型切换 Skill：支持在官方 OpenAI/GPT Codex 与第三方模型 provider 之间切换，并保持终端 `/resume` 历史共享。


## 已验证 Provider

- 官方 OpenAI/GPT Codex provider
- DeepSeek V4 via Moon Bridge
- 小米 MiMo v2.5 Pro via Moon Bridge，使用 `protocol: "openai-chat"`

GLM、Qwen、Kimi、内部 OpenAI-compatible API 等其他国产或自建 API，也可以按同一模式继续适配。前提是它们能通过 Moon Bridge、LiteLLM、OpenAI-compatible proxy 或其他桥接层暴露成 Codex 可启动的 provider/model。

## 它解决什么问题

DeepSeek 官方的 Codex CLI 接入指南推荐通过 Moon Bridge 桥接。照做之后确实能在 Codex 里跑 DeepSeek，但问题很快出现：当你想切回官方 GPT 时，之前在 DeepSeek 下的对话历史全部从 `/resume` 里消失；再切回去，GPT 的对话也找不到了。两个 provider 各管各的记忆，手动复制 `history.jsonl` 根本解决不了。

这不是 DeepSeek 的问题，也不是 Moon Bridge 的问题。这是 Codex `/resume` 的底层机制决定的：它不只看 `history.jsonl`，还同时读取 SQLite 里的 threads 表和 rollout transcript 的 `session_meta` 元数据，甚至会在启动时反向回填覆盖你的手动修改。换句话说，只改一个层面是徒劳的。

这个 Skill 把这些坑全部填平。核心思路是：**一个终端专用 `CODEX_HOME`，多个 provider 启动入口，同一批 CLI `/resume` 历史，VSCode/App 默认隔离。**

你在 GPT 下创建的对话，切到 DeepSeek 后 `/resume` 看得到；在 DeepSeek 下创建的对话，切回 GPT 后 `/resume` 同样看得到。不用手动复制文件，不用操心 SQLite 被覆盖，sync 脚本在启动 provider 前自动搞定一切。

这套机制不绑定特定模型厂商。最早为 DeepSeek via Moon Bridge 开发，后来验证了小米 MiMo v2.5 Pro。GLM、Qwen、Kimi、内部自建 API 等只要能通过 Moon Bridge、LiteLLM、OpenAI-compatible proxy 暴露成 Codex 可启动的 provider/model，都可以直接复用同一套流程。

## 关键发现

Codex 的 `/resume` 不只看 `history.jsonl`。

它还依赖：

- `state_*.sqlite` 里的 `threads` 表
- `sessions/**/rollout-*.jsonl` 第一行的 `session_meta`

更关键的是，Codex 启动时会从 rollout transcript 的 `session_meta.model_provider` 反向回填 SQLite。也就是说，只改 SQLite 会被覆盖回去；只复制 JSONL 也不够。

真正有效的修法是同时同步：

- `state_*.sqlite -> threads.model_provider / model / source / thread_source / has_user_event / archived`
- `sessions/**/rollout-*.jsonl` 第一行 `session_meta.model_provider`

本仓库的 `scripts/sync_resume_provider.py` 就是为这个坑写的。

## 仓库内容

```text
codex-model-switchboard/
├── SKILL.md
├── README.md
├── README.zh-CN.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── icon.svg
├── references/
│   └── provider-notes.md
└── scripts/
    ├── merge_codex_homes.py
    └── sync_resume_provider.py
```

## 安装

把这个仓库放进 Codex 的 skills 目录：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/Yichen-ZJU/codex-model-switchboard.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/codex-model-switchboard"
```

然后在 Codex 里调用：

```text
Use $codex-model-switchboard to configure Codex CLI model switching with shared /resume history.
```

## 典型用法

### 1. 合并多个 Codex Home

```bash
python scripts/merge_codex_homes.py \
  --target /path/to/codex-homes/cli \
  --source /home/yyc/.codex \
  --source /path/to/codex-deepseek-home
```

默认会排除 `source='vscode'` 的记录，避免把 VSCode/App 对话混进 CLI。

### 2. 切到第三方 provider 前同步

以 Moon Bridge provider 为例：

```bash
python scripts/sync_resume_provider.py \
  --codex-home /path/to/codex-homes/cli \
  --provider moonbridge \
  --model moonbridge
```

然后启动：

```bash
CODEX_HOME=/path/to/codex-homes/cli codex \
  -m moonbridge \
  -c 'model_provider="moonbridge"' \
  -c 'model_catalog_json="/path/to/codex-homes/cli/moonbridge_models_catalog.json"'
```

### 3. 切回官方 GPT 前同步

```bash
python scripts/sync_resume_provider.py \
  --codex-home /path/to/codex-homes/cli \
  --provider openai \
  --model gpt-5.5
```

然后正常启动：

```bash
CODEX_HOME=/path/to/codex-homes/cli codex
```

## 小米 MiMo 示例

MiMo v2.5 Pro 已验证可通过 OpenAI Chat Completions 兼容接口接入 Moon Bridge：

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

切换 `/resume` 可见性：

```bash
python scripts/sync_resume_provider.py \
  --codex-home /path/to/codex-homes/cli \
  --provider mimo \
  --model mimo-v2.5-pro
```

## 安全提醒

- 不要把 DeepSeek API Key、OpenAI Key、小米 token 或任何 token 提交进仓库。
- 不要把自定义 provider 命名为 `openai`，这是 Codex 内置保留名。
- 不建议全局设置 `model_catalog_json`，否则可能影响官方 GPT 模型列表。
- 修改 Codex home 前先备份，尤其是 `state_*.sqlite` 和 `sessions/`。

## 适合谁

适合已经在用 Codex CLI，并且希望：

- 官方 GPT、DeepSeek、MiMo、GLM、Qwen、Kimi 等 provider 来回切换
- 配额不足时使用备用模型
- CLI 历史和 `/resume` 不丢
- VSCode/App 对话保持隔离

这个 Skill 本质上是一次 Codex 多模型切换踩坑记录的工程化版本。后续国产 API 适配会持续补充。
