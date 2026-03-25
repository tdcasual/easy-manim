# HTTP Artifact Download Implementation Plan

## Goal
Add authenticated HTTP download endpoints for task artifacts so API clients can fetch `final_video.mp4`, scripts, previews, and validation reports without relying on Coolify, SSH, or Docker volume paths.

## Why
The current task result payload exposes `video-task://...` resource URIs, which work for MCP resource access but are awkward for HTTP-only clients and skills. A first-class HTTP artifact route makes the API self-contained for browser and automation workflows.

## Scope
- Add authenticated HTTP download route under `/api/tasks/{task_id}/artifacts/{artifact_path:path}`
- Reuse existing agent-scoped task authorization
- Infer MIME type from file extension
- Extend `/api/tasks/{task_id}/result` with convenience download URLs when artifacts exist
- Add integration tests for download success and agent scoping
- Document pure HTTP artifact retrieval in README and deploy runbook

## Out of Scope
- Signed public URLs
- CDN integration
- Range requests / streaming optimizations
- Bulk artifact archives

## Implementation Notes
1. Reuse `video-task://` resource resolution logic from `mcp_resources.py`
2. Expose a path resolver that returns a safe on-disk path within the task root
3. Use `FileResponse` in `http_api.py`
4. Keep error behavior simple:
   - 403 for cross-agent access
   - 404 for missing or invalid paths
5. Make result payload friendlier by including HTTP download URLs even when artifacts are only discovered from disk

## Validation
- `tests/integration/test_http_task_api.py`
- `tests/integration/test_http_artifact_download_api.py`

## Follow-up
Once deployed, update the private `easy-manim-video` skill to prefer HTTP downloads and only keep SSH/Coolify as an emergency fallback during rollout.
