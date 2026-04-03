import { afterEach, expect, test, vi } from "vitest";

import {
  appendVideoTurn,
  getVideoThreadIteration,
  getVideoThreadSurface,
  listVideoThreadParticipants,
  removeVideoThreadParticipant,
  requestVideoExplanation,
  requestVideoRevision,
  selectVideoResult,
  upsertVideoThreadParticipant,
} from "./videoThreadsApi";

afterEach(() => {
  vi.restoreAllMocks();
});

test("video thread api targets thread-native endpoints", async () => {
  const seen: Array<{ path: string; method: string; body?: string | null }> = [];

  globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://example.test");
    seen.push({
      path: url.pathname,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;

  await getVideoThreadSurface("thread-1", "sess-token-1");
  await getVideoThreadIteration("thread-1", "iter-1", "sess-token-1");
  await appendVideoTurn(
    "thread-1",
    {
      iteration_id: "iter-1",
      title: "Why this pacing?",
      summary: "Explain the slower opener.",
      addressed_participant_id: "repairer-1",
    },
    "sess-token-1"
  );
  await requestVideoRevision(
    "thread-1",
    "iter-1",
    { summary: "Slow the opener more.", preserve_working_parts: true },
    "sess-token-1"
  );
  await requestVideoExplanation(
    "thread-1",
    "iter-1",
    { summary: "Why did you choose this slower opening?" },
    "sess-token-1"
  );
  await selectVideoResult("thread-1", "iter-1", { result_id: "result-1" }, "sess-token-1");
  await listVideoThreadParticipants("thread-1", "sess-token-1");
  await upsertVideoThreadParticipant(
    "thread-1",
    {
      participant_id: "reviewer-1",
      participant_type: "agent",
      agent_id: "reviewer-1",
      role: "reviewer",
      display_name: "Reviewer",
      capabilities: ["review_bundle:read"],
    },
    "sess-token-1"
  );
  await removeVideoThreadParticipant("thread-1", "reviewer-1", "sess-token-1");

  expect(seen.map((item) => `${item.method} ${item.path}`)).toEqual([
    "GET /api/video-threads/thread-1/surface",
    "GET /api/video-threads/thread-1/iterations/iter-1",
    "POST /api/video-threads/thread-1/turns",
    "POST /api/video-threads/thread-1/iterations/iter-1/request-revision",
    "POST /api/video-threads/thread-1/iterations/iter-1/request-explanation",
    "POST /api/video-threads/thread-1/iterations/iter-1/select-result",
    "GET /api/video-threads/thread-1/participants",
    "POST /api/video-threads/thread-1/participants",
    "DELETE /api/video-threads/thread-1/participants/reviewer-1",
  ]);
  expect(seen[2]?.body).toContain('"addressed_participant_id":"repairer-1"');
  expect(seen[5]?.body).toContain('"result_id":"result-1"');
});
