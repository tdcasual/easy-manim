# Operator Console UI (Web)

This runbook covers running the human-facing operator console (`ui/`) against the local HTTP API.

## Prereqs

- Python venv set up (`.venv/`)
- The HTTP API running (default `http://127.0.0.1:8001`)
- Node.js + npm available for the UI

## Start The API

Use whatever API launch flow you already use locally. The UI expects `/api/*` and `/healthz` to be reachable.

## Start The UI

```bash
npm --prefix ui install
npm --prefix ui run dev
```

The UI dev server proxies `/api/*` and `/healthz` to `http://127.0.0.1:8001` via `ui/vite.config.ts`.

## Issue An Agent Token For Login

The UI login page expects an issued agent token.

Example:

```bash
source .venv/bin/activate
easy-manim-agent-admin --data-dir ./data issue-token --agent-id agent-a
```

Copy the returned `agent_token` value and paste it into the UI.

## Verification

```bash
npm --prefix ui test
npm --prefix ui run build
npm --prefix ui run e2e
```

The Playwright E2E tests in `ui/tests/e2e/*` mock the `/api/*` responses so they run without a backend.

