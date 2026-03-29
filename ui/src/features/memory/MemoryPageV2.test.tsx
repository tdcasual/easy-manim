import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { MemoryPageV2 } from "./MemoryPageV2";

test("renders translated persistent memory status and retrieval diagnostics", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/memory/session/summary") {
      return new Response(
        JSON.stringify({
          session_id: "sess-1",
          agent_id: "agent-a",
          entry_count: 1,
          summary_text: "系统会记住最近一次工作偏好",
          lineage_refs: [],
          summary_digest: "digest-a",
          entries: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/memories" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              memory_id: "mem-1",
              agent_id: "agent-a",
              source_session_id: "sess-1",
              status: "disabled",
              summary_text: "旧偏好已经停用",
              summary_digest: "digest-m1",
              lineage_refs: [],
              created_at: "2030-01-01T00:00:00Z",
              disabled_at: "2030-01-02T00:00:00Z",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/memories/retrieve" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          items: [
            {
              memory_id: "mem-1",
              score: 0.93,
              summary_text: "旧偏好已经停用",
              summary_digest: "digest-m1",
              matched_terms: ["teaching"],
              match_reasons: ["phrase_match", "keyword_overlap"],
              lineage_refs: [],
              enhancement: {},
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter>
      <MemoryPageV2 />
    </MemoryRouter>
  );

  expect(await screen.findByText("mem-1")).toBeInTheDocument();
  expect(screen.getByText("已停用")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/memory retrieval query/i), {
    target: { value: "teaching" },
  });
  fireEvent.click(screen.getByRole("button", { name: /inspect retrieval/i }));

  expect(await screen.findByText(/matched terms: teaching/i)).toBeInTheDocument();
  expect(screen.getByText(/reasons: phrase_match, keyword_overlap/i)).toBeInTheDocument();
});
