import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { MemoryPage } from "./MemoryPage";

test("supports clearing session memory, promoting, and disabling a persistent memory", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), init });
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
    if (path === "/api/memory/session" && init?.method === "DELETE") {
      return new Response(JSON.stringify({ cleared: true, entry_count: 0 }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    if (path === "/api/memories/promote" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          memory_id: "mem-2",
          agent_id: "agent-a",
          source_session_id: "sess-1",
          status: "active",
          summary_text: "Promoted memory.",
          summary_digest: "digest-m2",
          lineage_refs: [],
          snapshot: {},
          enhancement: {},
          created_at: "2030-01-01T00:00:00Z",
          disabled_at: null
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/memories/mem-1/disable" && init?.method === "POST") {
      return new Response(JSON.stringify({ memory_id: "mem-1", status: "disabled" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter>
      <MemoryPage />
    </MemoryRouter>
  );

  expect(await screen.findByText("mem-1")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /清空会话/i }));
  await waitFor(() => {
    expect(calls.some((c) => c.url.includes("/api/memory/session") && c.init?.method === "DELETE")).toBe(true);
  });

  await user.click(screen.getByRole("button", { name: /提升为长期记忆/i }));
  await waitFor(() => {
    expect(calls.some((c) => c.url.includes("/api/memories/promote") && c.init?.method === "POST")).toBe(true);
  });

  await user.click(screen.getByRole("button", { name: /停用/i }));
  await waitFor(() => {
    expect(calls.some((c) => c.url.includes("/api/memories/mem-1/disable") && c.init?.method === "POST")).toBe(true);
  });
});
