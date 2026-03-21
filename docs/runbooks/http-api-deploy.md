# HTTP API Deploy

## Goal
Run `easy-manim-api` as a plain HTTP JSON service for named agents that log in once, reuse an opaque session token, and access only their own tasks, memories, profile updates, and eval summaries.

## Start the service
```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-api --host 127.0.0.1 --port 8001 --data-dir data --no-embedded-worker
easy-manim-worker --data-dir data
```

## Provision an agent
```bash
source .venv/bin/activate
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
- keep `easy-manim-worker` running whenever `easy-manim-api` starts with `--no-embedded-worker`
- use HTTPS and a secret-bearing reverse proxy in production-like environments
- the HTTP API is agent-scoped: task reads, persistent memory, profile suggestions, and `/api/profile/evals` are filtered to the authenticated `agent_id`
