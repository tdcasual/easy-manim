# HTTP API Deploy

## Goal
Run `easy-manim-api` as a plain HTTP JSON service for named agents that log in once, reuse an opaque session token, and access only their own tasks, memories, profile updates, and eval summaries.

## Start with Docker Compose
```bash
cp .env.example .env
docker login ghcr.io -u <github-user>
docker compose pull
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:8001/healthz
```

If you are running against a real LLM provider, copy the required LiteLLM-backed `EASY_MANIM_LLM_*` values from `.env.beta.example` into `.env` before `docker compose up -d`.

This starts:

- `bootstrap` once to apply SQLite migrations on the shared `/app/data` volume
- `api` at `http://127.0.0.1:8001`
- `ui` at `http://127.0.0.1:8080`
- `worker` on the shared `/app/data` volume

`api`, `worker`, and optional `mcp` wait for the bootstrap job to finish successfully before they start.

Enable the optional MCP transport only when needed:

```bash
docker compose --profile mcp up -d mcp
```

For local source builds instead of pulling published GHCR images:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build -d
```

## Start the service
```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-db-bootstrap --data-dir data
easy-manim-api --host 127.0.0.1 --port 8001 --data-dir data --no-embedded-worker
easy-manim-worker --data-dir data
```

## Provision an agent
Using the Compose stack:

```bash
docker compose run --rm api \
  easy-manim-agent-admin --data-dir /app/data create-profile --agent-id agent-a --name "Agent A"

docker compose run --rm api \
  easy-manim-agent-admin --data-dir /app/data issue-token --agent-id agent-a
```

Using a local Python environment:

```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-agent-admin --data-dir data create-profile --agent-id agent-a --name "Agent A"
easy-manim-agent-admin --data-dir data issue-token --agent-id agent-a
```

Store the plaintext token securely. The database only keeps `token_hash`.

## Login and create a session
```bash
SESSION_TOKEN=$(
  curl -s http://127.0.0.1:8001/api/sessions \
    -H 'content-type: application/json' \
    -d '{"agent_token":"<plaintext-agent-token>"}' | jq -r '.session_token'
)
```

## Common calls
```bash
curl -s http://127.0.0.1:8001/api/whoami \
  -H "Authorization: Bearer ${SESSION_TOKEN}"

curl -s http://127.0.0.1:8001/api/tasks \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -d '{"prompt":"draw a blue circle"}'

curl -s http://127.0.0.1:8001/api/profile \
  -H "Authorization: Bearer ${SESSION_TOKEN}"

curl -s http://127.0.0.1:8001/api/profile/evals \
  -H "Authorization: Bearer ${SESSION_TOKEN}"
```

## Session lifecycle
- `POST /api/sessions` exchanges a plaintext agent token for an opaque session token
- send `Authorization: Bearer <session_token>` on every authenticated request
- `DELETE /api/sessions/current` revokes the active session token
- revoked or expired session tokens should return `401`

## Deployment notes
- run `easy-manim-db-bootstrap --data-dir <data-dir>` before starting local API, MCP, worker, eval, cleanup, or agent-admin processes outside Compose
- keep `easy-manim-worker` running whenever `easy-manim-api` starts with `--no-embedded-worker`
- the default [docker-compose.yml](/Users/lvxiaoer/Documents/codeWork/easy-manim/docker-compose.yml) expects published GHCR images, while [docker-compose.build.yml](/Users/lvxiaoer/Documents/codeWork/easy-manim/docker-compose.build.yml) adds local source builds
- use HTTPS and a secret-bearing reverse proxy in production-like environments
- the HTTP API is agent-scoped: task reads, persistent memory, profile suggestions, and `/api/profile/evals` are filtered to the authenticated `agent_id`
