import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { ProfilePage } from "./ProfilePage";

test("renders current profile and scorecard, and allows applying a patch", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile") {
      return new Response(
        JSON.stringify({
          agent_id: "agent-a",
          name: "Agent A",
          status: "active",
          profile_version: 1,
          profile_json: { style_hints: { tone: "warm" }, output_profile: { length: "short" }, validation_profile: {} },
          policy_json: {},
          created_at: "2030-01-01T00:00:00Z",
          updated_at: "2030-01-01T00:00:00Z"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/profile/scorecard") {
      return new Response(
        JSON.stringify({
          completed_count: 3,
          failed_count: 1,
          failed_count_recent: 1,
          median_quality_score: 0.8,
          top_issue_codes: ["bad_color"],
          recent_profile_digests: ["digest-a"]
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/profile/suggestions" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: [] }), { status: 200, headers: { "content-type": "application/json" } });
    }
    if (path === "/api/profile/apply" && init?.method === "POST") {
      return new Response(JSON.stringify({ applied: true }), { status: 200, headers: { "content-type": "application/json" } });
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter>
      <ProfilePage />
    </MemoryRouter>
  );

  expect(await screen.findByText(/agent a/i)).toBeInTheDocument();
  expect(screen.getByText(/completed/i)).toBeInTheDocument();
  expect(screen.getByText("3")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText(/patch/i), {
    target: { value: JSON.stringify({ style_hints: { tone: "editorial" } }) }
  });
  await user.click(screen.getByRole("button", { name: /apply patch/i }));

  await waitFor(() => {
    expect(calls.some((c) => c.url.includes("/api/profile/apply"))).toBe(true);
  });
});
