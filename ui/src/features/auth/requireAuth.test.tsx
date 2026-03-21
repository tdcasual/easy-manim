import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "../../app/App";
import { clearSessionToken, writeSessionToken } from "../../lib/session";

test("unauthenticated access to protected routes renders login page", () => {
  clearSessionToken();

  render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <App />
    </MemoryRouter>
  );

  expect(screen.getByRole("heading", { name: /log in/i })).toBeInTheDocument();
});

test("authenticated access to protected routes renders the requested page", async () => {
  writeSessionToken("sess-token-1");

  // Default Tasks page will try to load `/api/tasks`; keep the test deterministic.
  // @ts-expect-error - test shim
  globalThis.fetch = async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    return new Response("not found", { status: 404 });
  };

  render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <App />
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: /^tasks$/i })).toBeInTheDocument();
  expect(await screen.findByText(/no tasks yet/i)).toBeInTheDocument();
});
