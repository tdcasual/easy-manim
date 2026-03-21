import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { SuggestionsPanel } from "./SuggestionsPanel";

test("lists suggestions and allows generating, applying, and dismissing", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  const suggestions: Array<any> = [
    {
      suggestion_id: "sug-1",
      agent_id: "agent-a",
      status: "pending",
      patch_json: { style_hints: { tone: "warm" } },
      rationale_json: { reason: "Operator requested it." },
      provenance_json: {},
      created_at: "2030-01-01T00:00:00Z",
      applied_at: null
    }
  ];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile/suggestions" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: suggestions }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    if (path === "/api/profile/suggestions/generate" && init?.method === "POST") {
      suggestions.unshift({
        suggestion_id: "sug-2",
        agent_id: "agent-a",
        status: "pending",
        patch_json: { output_profile: { length: "short" } },
        rationale_json: {},
        provenance_json: {},
        created_at: "2030-01-01T00:00:00Z",
        applied_at: null
      });
      return new Response(JSON.stringify({ items: suggestions }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    if (path === "/api/profile/suggestions/sug-1/apply" && init?.method === "POST") {
      return new Response(JSON.stringify({ applied: true, suggestion: { ...suggestions[0], status: "applied" } }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    if (path === "/api/profile/suggestions/sug-1/dismiss" && init?.method === "POST") {
      return new Response(
        JSON.stringify({ dismissed: true, suggestion: { ...suggestions[0], status: "dismissed" } }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter>
      <SuggestionsPanel />
    </MemoryRouter>
  );

  expect(await screen.findByText("sug-1")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /generate suggestions/i }));
  expect(await screen.findByText("sug-2")).toBeInTheDocument();

  // Apply sug-1 specifically (avoid ambiguity after generate inserts sug-2).
  await user.click(screen.getAllByRole("button", { name: /^apply$/i })[1]);
  await waitFor(() => {
    expect(calls.some((c) => c.url.includes("/api/profile/suggestions/sug-1/apply"))).toBe(true);
  });

  await user.click(screen.getAllByRole("button", { name: /^dismiss$/i })[1]);
  await waitFor(() => {
    expect(calls.some((c) => c.url.includes("/api/profile/suggestions/sug-1/dismiss"))).toBe(true);
  });
});
