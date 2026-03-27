# Agent Self-Serve Deployment and Usage

## Goal
Give an autonomous agent a single document it can follow to deploy `easy-manim` on one server and start using it without reading the whole codebase first.

## What This Project Actually Runs
`easy-manim` is a local-first Manim video generation service with four runtime surfaces:

| Component | Purpose | Default Port | Required |
| --- | --- | --- | --- |
| `api` | Plain HTTP JSON API for login, tasks, memory, profile, and eval endpoints | `8001` | yes |
| `worker` | Background task processor that performs generation, rendering, and validation | none | yes |
| `ui` | Human operator console served by Nginx | `8080` | no for agent-only use |
| `mcp` | Optional MCP endpoint over streamable HTTP | `8000` | no |

Important architectural constraints:

- The service is designed for a single host.
- State lives in SQLite plus a local filesystem volume under `/app/data`.
- A one-shot `bootstrap` job must apply SQLite migrations before `api`, `worker`, or `mcp` starts.
- Horizontal multi-writer deployment is not the current target.
- The backend image includes Python, `manim`, `ffmpeg`, and `ffprobe`.
- The stock backend image does not install a LaTeX toolchain, so prompts that depend on `MathTex` or `Tex` need either a custom image or a non-formula workload.

## Recommended Access Pattern
- Use the HTTP API for most autonomous agents.
- Use MCP only when the caller is already MCP-native.
- Keep the MCP endpoint private or internal-only.
- Put the HTTP API and UI behind HTTPS if the server is reachable outside a trusted network.

## Image Tags To Use
The GitHub Actions workflow publishes both images to GHCR:

- backend: `ghcr.io/tdcasual/easy-manim`
- ui: `ghcr.io/tdcasual/easy-manim-ui`

Typical tags:

- `latest`
- `main`
- `sha-<git_sha>`

For stable rollouts, pin both images to the same `sha-<git_sha>` tag.

## Files To Place On The Server
Create a deployment directory on the server, for example `/opt/easy-manim`, and put the following two files there.

### `compose.yaml`
```yaml
services:
  bootstrap:
    image: ghcr.io/tdcasual/easy-manim:latest
    init: true
    restart: "no"
    env_file:
      - .env
    environment: &backend-environment
      PYTHONUNBUFFERED: "1"
    command:
      - easy-manim-db-bootstrap
      - --data-dir
      - /app/data
    volumes:
      - easy_manim_data:/app/data

  api:
    image: ghcr.io/tdcasual/easy-manim:latest
    init: true
    restart: unless-stopped
    depends_on:
      bootstrap:
        condition: service_completed_successfully
    env_file:
      - .env
    environment:
      PYTHONUNBUFFERED: "1"
    command:
      - easy-manim-api
      - --host
      - 0.0.0.0
      - --port
      - "8001"
      - --data-dir
      - /app/data
      - --no-embedded-worker
    volumes:
      - easy_manim_data:/app/data
    ports:
      - "8001:8001"
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - import urllib.request; urllib.request.urlopen("http://127.0.0.1:8001/healthz", timeout=5).read()
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 20s

  worker:
    image: ghcr.io/tdcasual/easy-manim:latest
    init: true
    restart: unless-stopped
    depends_on:
      bootstrap:
        condition: service_completed_successfully
    env_file:
      - .env
    environment:
      <<: *backend-environment
    command:
      - easy-manim-worker
      - --data-dir
      - /app/data
    volumes:
      - easy_manim_data:/app/data

  ui:
    image: ghcr.io/tdcasual/easy-manim-ui:latest
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped
    ports:
      - "8080:80"

  mcp:
    image: ghcr.io/tdcasual/easy-manim:latest
    profiles:
      - mcp
    init: true
    restart: unless-stopped
    depends_on:
      bootstrap:
        condition: service_completed_successfully
    env_file:
      - .env
    environment:
      <<: *backend-environment
    command:
      - easy-manim-mcp
      - --transport
      - streamable-http
      - --host
      - 0.0.0.0
      - --port
      - "8000"
      - --data-dir
      - /app/data
      - --no-embedded-worker
    volumes:
      - easy_manim_data:/app/data
    ports:
      - "8000:8000"

volumes:
  easy_manim_data:
```

### `.env`
```dotenv
# Deployment overrides for the stock container images.
# The backend image already ships safe defaults for auth mode, command paths,
# worker timings, queue limits, and conservative feature flags.
# Keep this file focused on values that commonly vary per deployment.

EASY_MANIM_LLM_PROVIDER=stub
EASY_MANIM_LLM_MODEL=stub-manim-v1
EASY_MANIM_LLM_API_BASE=
EASY_MANIM_LLM_API_KEY=

# Optional provider tuning overrides
# EASY_MANIM_LLM_TIMEOUT_SECONDS=60
# EASY_MANIM_LLM_MAX_RETRIES=2

# Optional runtime overrides
# EASY_MANIM_AUTH_MODE=required
# EASY_MANIM_DEFAULT_QUALITY_PRESET=development
# EASY_MANIM_RENDER_TIMEOUT_SECONDS=300
# EASY_MANIM_WORKER_ID=worker-1
# EASY_MANIM_MCP_PORT=8000
```

If you want a real upstream model instead of deterministic `stub` mode, change the provider block to:

```dotenv
EASY_MANIM_LLM_PROVIDER=litellm
EASY_MANIM_LLM_MODEL=openai/gpt-4.1-mini
EASY_MANIM_LLM_API_BASE=https://api.openai.com/v1
EASY_MANIM_LLM_API_KEY=<real-secret>
```

## Bring The Stack Up
```bash
cd /opt/easy-manim
docker login ghcr.io -u <github-user>
docker compose pull
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:8001/healthz
docker compose exec api easy-manim-doctor --data-dir /app/data --json
```

`docker compose up -d` runs the one-shot `bootstrap` service first, and `api`, `worker`, and optional `mcp` wait for it to finish successfully.

Enable MCP only when you need it:

```bash
docker compose --profile mcp up -d mcp
```

For formula-heavy prompts, verify the runtime explicitly:

```bash
docker compose exec api easy-manim-doctor --data-dir /app/data --json --require-latex
```

If that command fails on the stock image, you need to extend the backend image with LaTeX and `dvisvgm` before accepting `MathTex` or `Tex` workloads.

## Provision An Agent Identity
Create an agent profile and issue a plaintext token:

```bash
docker compose run --rm api \
  easy-manim-agent-admin --data-dir /app/data create-profile \
  --agent-id agent-a \
  --name "Agent A"

docker compose run --rm api \
  easy-manim-agent-admin --data-dir /app/data issue-token \
  --agent-id agent-a
```

`issue-token` prints the plaintext `agent_token` once. Store it securely. The database keeps only a token hash.

Optional per-agent defaults can be attached at profile creation time:

```bash
docker compose run --rm api \
  easy-manim-agent-admin --data-dir /app/data create-profile \
  --agent-id teaching-agent \
  --name "Teaching Agent" \
  --profile-json '{"style_hints":{"tone":"teaching","pace":"steady"}}'
```

## Recommended Agent Flow: HTTP API
The HTTP API is the cleanest self-serve path for most agents.

### 1. Log in once
```bash
export AGENT_TOKEN='<plaintext-agent-token>'

SESSION_TOKEN=$(
  curl -fsS http://127.0.0.1:8001/api/sessions \
    -H 'content-type: application/json' \
    -d "{\"agent_token\":\"${AGENT_TOKEN}\"}" | jq -r '.session_token'
)
```

### 2. Verify identity
```bash
curl -fsS http://127.0.0.1:8001/api/whoami \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq
```

### 3. Create a task
```bash
TASK_ID=$(
  curl -fsS http://127.0.0.1:8001/api/tasks \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer ${SESSION_TOKEN}" \
    -d '{
      "prompt": "draw a blue circle",
      "style_hints": {"tone": "teaching"},
      "output_profile": {"quality_preset": "development"}
    }' | jq -r '.task_id'
)
```

### 4. Poll until terminal status
```bash
while true; do
  SNAPSHOT=$(curl -fsS "http://127.0.0.1:8001/api/tasks/${TASK_ID}" \
    -H "Authorization: Bearer ${SESSION_TOKEN}")
  STATUS=$(printf '%s' "${SNAPSHOT}" | jq -r '.status')
  printf 'task=%s status=%s\n' "${TASK_ID}" "${STATUS}"
  if [ "${STATUS}" = "completed" ] || [ "${STATUS}" = "failed" ] || [ "${STATUS}" = "cancelled" ]; then
    printf '%s\n' "${SNAPSHOT}" | jq
    break
  fi
  sleep 2
done
```

### 5. Fetch the result
```bash
curl -fsS "http://127.0.0.1:8001/api/tasks/${TASK_ID}/result" \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq
```

For completed tasks, the result payload includes a `video_resource` URI that points at the final MP4 inside the task artifact tree.

### 6. Optional memory and profile endpoints
```bash
curl -fsS http://127.0.0.1:8001/api/memory/session \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq

curl -fsS http://127.0.0.1:8001/api/memory/session/summary \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq

curl -fsS http://127.0.0.1:8001/api/profile \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq

curl -fsS http://127.0.0.1:8001/api/profile/scorecard \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq
```

### 7. Log out when done
```bash
curl -fsS -X DELETE http://127.0.0.1:8001/api/sessions/current \
  -H "Authorization: Bearer ${SESSION_TOKEN}" | jq
```

## MCP Flow For MCP-Native Agents
If your caller already speaks MCP:

1. start the optional `mcp` service with `docker compose --profile mcp up -d mcp`
2. connect the MCP client to `http://<host>:8000/mcp`
3. call `authenticate_agent(agent_token)` once if `EASY_MANIM_AUTH_MODE=required`
4. use tools such as:
   - `create_video_task`
   - `get_video_task`
   - `get_video_result`
   - `revise_video_task`
   - `retry_video_task`
   - `get_session_memory`
   - `summarize_session_memory`
   - `list_agent_memories`
   - `get_runtime_status`
5. use resources such as:
   - `video-task://{task_id}/task.json`
   - `video-task://{task_id}/artifacts/current_script.py`
   - `video-task://{task_id}/artifacts/final_video.mp4`
   - `video-task://{task_id}/logs/events.jsonl`
   - `video-task://{task_id}/validations/{report_name}`

## Human Console
The UI is optional for agents but useful for operators.

- open `http://<host>:8080`
- paste the plaintext `agent_token` into the login screen
- browse tasks, memory, profile, and eval views

The UI talks to the same HTTP API on port `8001`.

## Validation Checklist
After deployment, the stack is healthy when all of the following are true:

- `docker compose ps` shows `api`, `worker`, and `ui` as running
- `curl http://127.0.0.1:8001/healthz` returns `{"status":"ok"}`
- `docker compose exec api easy-manim-doctor --data-dir /app/data --json` exits successfully
- agent login through `POST /api/sessions` returns a `session_token`
- a test task reaches `completed`, `failed`, or `cancelled` instead of hanging in `queued`

## Operational Notes
- Keep `api` and `worker` on the same `/app/data` volume.
- Do not run multiple writers against the same SQLite file from different hosts.
- Deleting the `easy_manim_data` volume also deletes the task database, issued tokens, memories, and task artifacts.
- `stub` mode is the safest default for smoke tests because it does not require real provider credentials.
- Real provider traffic should be gated behind secrets management and HTTPS.

## Rollback Strategy
Pin both images to a matching `sha-<git_sha>` tag and only change tags during an upgrade. Example:

```yaml
image: ghcr.io/tdcasual/easy-manim:sha-66991ef
image: ghcr.io/tdcasual/easy-manim-ui:sha-66991ef
```

Then redeploy:

```bash
docker compose pull
docker compose up -d
```

## Pointers For Deeper Detail
- `README.md`
- `docs/runbooks/http-api-deploy.md`
- `docs/runbooks/local-dev.md`
- `docs/runbooks/operator-console-ui.md`
