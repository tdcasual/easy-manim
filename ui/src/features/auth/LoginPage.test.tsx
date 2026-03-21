import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { LoginPage } from "./LoginPage";

test("stores session token after successful login", async () => {
  const user = userEvent.setup();
  const fetchCalls: Array<{ url: string; init?: RequestInit }> = [];

  // @ts-expect-error - test shim
  globalThis.fetch = async (url: string, init?: RequestInit) => {
    fetchCalls.push({ url, init });
    if (String(url).endsWith("/api/sessions")) {
      return new Response(
        JSON.stringify({
          session_token: "sess-token-1",
          agent_id: "agent-a",
          name: "Agent A",
          expires_at: "2030-01-01T00:00:00Z"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  };

  localStorage.clear();

  render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );

  await user.type(screen.getByLabelText(/agent token/i), "easy-manim.agent-a.secret");
  await user.click(screen.getByRole("button", { name: /log in/i }));

  await waitFor(() => {
    expect(localStorage.getItem("easy_manim_session_token")).toBe("sess-token-1");
  });
  expect(fetchCalls.some((call) => call.url.toString().includes("/api/sessions"))).toBe(true);
});

