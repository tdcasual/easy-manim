# Container Image And Compose Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add GitHub Actions workflows that build and publish deployable container images, then ship a complete Docker Compose deployment path for the backend, worker, optional MCP endpoint, and operator UI.

**Architecture:** Split the container story into two image artifacts: one Python application image for the API, worker, MCP server, and admin/eval CLI usage, plus one static UI image served by Nginx with reverse proxy rules to the API container. Make `docker-compose.yml` deployment-first by pulling tagged images from GHCR, and provide a build override file so the same topology can still be exercised locally from source.

**Tech Stack:** Docker, Docker Compose, GitHub Actions, GHCR, Python 3.13, Node 20, Nginx, Vite, existing `easy-manim-api`, `easy-manim-worker`, `easy-manim-mcp`, and `@superpowers:verification-before-completion`.

---

## Task 1: Make the backend image publish-ready

**Files:**
- Modify: `Dockerfile`
- Modify: `.dockerignore`

**Step 1: Audit the current image contract**

Confirm which commands need to run from the backend image:

1. `easy-manim-api`
2. `easy-manim-worker`
3. `easy-manim-mcp`
4. `easy-manim-agent-admin`
5. `easy-manim-eval-run`

Expected finding: the image should contain the Python package, runtime system dependencies, and `evals/`, but does not need tests copied into the final runtime image.

**Step 2: Write minimal backend image improvements**

Update the Dockerfile so it:

1. installs runtime system packages needed by Manim
2. copies only the files required to install and run the app
3. exposes both API and MCP ports
4. defaults to a deploy-friendly API command while allowing Compose to override commands
5. preserves `/app/data` as the runtime data location

**Step 3: Tighten Docker build context**

Update `.dockerignore` to avoid sending virtualenv, git metadata, UI build output, and other local-only files into backend builds.

**Step 4: Verify image config**

Run:

```bash
docker build -f Dockerfile .
```

Expected: successful backend image build.

## Task 2: Add a deployable UI image

**Files:**
- Create: `ui/Dockerfile`
- Create: `ui/nginx.conf`
- Create: `ui/.dockerignore`

**Step 1: Define the runtime shape**

Use a multi-stage UI image:

1. Node stage builds the Vite app
2. Nginx stage serves the built assets
3. Nginx proxies `/api/*` and `/healthz` to the Compose `api` service
4. SPA routes fall back to `index.html`

**Step 2: Implement the image**

Build from `ui/package-lock.json` with `npm ci`, then copy only `dist/` and nginx config into the final image.

**Step 3: Verify the UI image**

Run:

```bash
docker build -f ui/Dockerfile ui
```

Expected: successful UI image build.

## Task 3: Replace the minimal Compose file with a full deployment topology

**Files:**
- Modify: `docker-compose.yml`
- Create: `docker-compose.build.yml`

**Step 1: Define the deployment topology**

`docker-compose.yml` should include:

1. `api`
2. `worker`
3. `ui`
4. optional `mcp` profile

Shared behaviors:

1. named volume for `/app/data`
2. restart policy
3. shared environment contract
4. healthcheck for the API
5. image references pointing at GHCR by default

**Step 2: Preserve local source builds**

Add `docker-compose.build.yml` as a local override that injects `build:` sections for both backend and UI services, so local verification can still use:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

**Step 3: Verify Compose resolution**

Run:

```bash
docker compose config
docker compose -f docker-compose.yml -f docker-compose.build.yml config
```

Expected: both configs render without schema errors.

## Task 4: Add GitHub Actions image builds and publishing

**Files:**
- Create: `.github/workflows/docker-images.yml`

**Step 1: Define image outputs**

Publish:

1. `ghcr.io/<owner>/easy-manim`
2. `ghcr.io/<owner>/easy-manim-ui`

**Step 2: Implement workflow behavior**

The workflow should:

1. run on pushes to the default branch, tags, pull requests, and manual dispatch
2. build both images via a matrix
3. push only when the event is not a pull request
4. use Buildx caching
5. generate OCI labels and tags from branch, tag, SHA, and default-branch `latest`

**Step 3: Verify workflow syntax**

Run a YAML sanity check and ensure the new workflow aligns with current repo conventions.

## Task 5: Document how to use the images and Compose deployment

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/http-api-deploy.md`

**Step 1: Update the README container section**

Document:

1. which images are built
2. how to start the deployment stack from GHCR
3. how to use the local build override
4. how to enable the optional MCP profile

**Step 2: Update deployment runbook**

Add concrete operational commands for:

1. pulling images
2. starting services
3. issuing an agent token through the Compose stack
4. checking health

**Step 3: Final verification**

Run the most relevant verification commands after edits:

```bash
docker compose config
docker compose -f docker-compose.yml -f docker-compose.build.yml config
docker build -f ui/Dockerfile ui
python -m pytest -q
npm --prefix ui run build
```

Expected: configuration resolves and existing project tests/builds remain green.
