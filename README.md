# ChatBI Agent — AI Supply Chain Analyst

> Built on **EdgeOne Makers** with **Harness Engineering** 6-layer architecture.
> Deploy: [![EdgeOne Makers](https://img.shields.io/badge/EdgeOne-Makers-blue)](https://pages.edgeone.ai)

## Overview

ChatBI Agent is an intelligent supply chain data analyst. Upload CSV/Excel files and ask questions — the agent uses sandbox tools (Python, files, shell) to perform EDA, forecasting, ABC/XYZ classification, inventory optimization, and pricing analysis.

### Architecture

```
chatbi-agent-starter/
├── agents/                  # Agent endpoints (stateful)
│   ├── chat/index.py        #   POST /chat — SSE streaming + tool calling
│   └── stop/index.py        #   POST /stop  — abort active run
├── cloud-functions/         # Stateless CRUD endpoints
│   ├── conversations/       #   List user conversations
│   ├── history/             #   Load conversation messages
│   └── delete-conversation/ #   Delete a conversation
├── harness/                 # Harness Engineering 6-layer framework
│   ├── spec/                #   L1: Task specifications (7 tasks)
│   ├── skills/              #   L2: Reusable analysis skills
│   ├── agents/              #   L3: Role definitions (7 agent roles)
│   ├── workflows/           #   L3: Workflow definitions (5 workflows)
│   ├── memory/              #   L4: Decisions + lessons learned
│   ├── evaluation/          #   L5: Quality gates + metrics
│   ├── rules/               #   L6: Hard constraints
│   └── scripts/             #   L6: Validation scripts
├── index.html               # React SPA frontend
├── edgeone.json             # EdgeOne Makers config
└── package.json             # Vite + React dependencies
```

## Features

| Feature | Description |
|---------|-------------|
| 📊 **EDA** | Automated exploratory data analysis |
| 🔮 **Forecasting** | Demand forecasting with statistical models |
| 📦 **ABC/XYZ** | Inventory classification |
| 📉 **Inventory** | Safety stock & ROP optimization |
| 💰 **Pricing** | Competitive pricing analysis |
| 📄 **File Upload** | CSV, Excel, JSON support |
| 💬 **Conversations** | Multi-session with sidebar history |
| 🛠 **Sandbox** | Real Python execution (pandas, numpy, matplotlib) |
| 🔄 **Streaming** | Real-time SSE token streaming |
| 🧠 **Memory** | Persistent conversation storage |

## Getting Started

### Prerequisites
- Node.js ≥ 18
- EdgeOne Makers account
- [EdgeOne CLI](https://www.npmjs.com/package/edgeone): `npm install -g edgeone`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_GATEWAY_API_KEY` | EdgeOne AI Gateway API key | (required) |
| `AI_GATEWAY_BASE_URL` | Gateway base URL | `https://ai-gateway.edgeone.link/v1` |
| `AI_GATEWAY_MODEL` | Model to use | `@makers/deepseek-v4-flash` |

### Local Development

```bash
npm install
npx vite dev        # Frontend on :5173
```

> The Vite dev server proxies `/chat`, `/stop`, `/history`, `/conversations`, `/delete-conversation` to `localhost:8088`.

### Deploy

```bash
edgeone makers deploy
```

## Harness Framework

ChatBI follows the **Harness Engineering** methodology:

| Layer | Name | Purpose |
|-------|------|---------|
| L1 | Information Boundary | `spec/` — defines what the agent should do |
| L2 | Tool System | `skills/` — standardized analysis procedures |
| L3 | Execution Orchestration | `agents/` + `workflows/` — roles + task flows |
| L4 | Memory & State | `memory/` — decisions, lessons, state tracking |
| L5 | Evaluation & Observability | `evaluation/` — quality gates, metrics |
| L6 | Constraints & Recovery | `rules/` + `scripts/` — hard rules + validation |

When analyzing data, the agent references `harness/spec/tasks/` for task definitions and `harness/workflows/` for analysis workflows.

## API Endpoints

### `POST /chat`
SSE streaming chat with tool calling.

**Request:** `{ message: string, files?: [{name, content, mimeType}] }`
**Headers:** `makers-conversation-id: <uuid>`
**Response:** SSE stream with events:
- `model_info` — active model name
- `status` — `thinking` | `executing`
- `tool_call` — sandbox tool invocation
- `tool_result` — tool execution result
- `ai_response` — streaming text chunks
- `[DONE]` — stream complete

### `POST /stop`
Abort the active agent run.

### `POST /conversations`
List user's conversations.

### `POST /history`
Load messages for a conversation.

### `POST /delete-conversation`
Delete a conversation permanently.

## Tech Stack

- **Backend:** Python (Gateway Direct pattern on EdgeOne AI Gateway)
- **Frontend:** React 18, ReactMarkdown, remark-gfm
- **Build:** Vite 5, TypeScript
- **Platform:** EdgeOne Makers (Tencent Cloud)
- **Model:** DeepSeek V4 Flash (via `@makers/` prefix)

## License

MIT
