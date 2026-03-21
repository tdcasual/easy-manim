# easy-manim Operator Console (UI)

This folder contains the human-facing web console for `easy-manim`.

## Local Development

1. Start the API server (defaults to `http://127.0.0.1:8001`).
2. Start the UI dev server:

```bash
npm --prefix ui install
npm --prefix ui run dev
```

The UI dev server proxies `/api/*` and `/healthz` to `http://127.0.0.1:8001` (see `ui/vite.config.ts`).

## Login (Agent Token)

The console uses the existing opaque agent token flow:

1. Issue a token with the admin CLI (example):

```bash
source .venv/bin/activate
easy-manim-agent-admin --data-dir ./data issue-token --agent-id agent-a
```

2. Copy the returned `agent_token` and paste it into the UI login page.

## Tests

```bash
npm --prefix ui test
npm --prefix ui run build
npm --prefix ui run e2e
```

The E2E tests in `ui/tests/e2e/*` use mocked `/api/*` responses so they can run without a backend.
