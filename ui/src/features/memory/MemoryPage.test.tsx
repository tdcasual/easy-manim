import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { MemoryPage } from "./MemoryPage";

test("renders session memory summary and persistent memories", async () => {
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
          summary_text: "We prefer short, friendly prompts.",
          lineage_refs: [],
          summary_digest: "digest-a",
          entries: []
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
              status: "active",
              summary_text: "Operator prefers clear labels.",
              summary_digest: "digest-m1",
              lineage_refs: [],
              snapshot: {},
              enhancement: {},
              created_at: "2030-01-01T00:00:00Z",
              disabled_at: null
            }
          ]
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter>
      <MemoryPage />
    </MemoryRouter>
  );

  expect(await screen.findByText(/we prefer short/i)).toBeInTheDocument();
  expect(screen.getByText("mem-1")).toBeInTheDocument();
});

