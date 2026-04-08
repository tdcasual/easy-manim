import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";
import { writeSessionToken } from "../lib/session";

test("renders the operator console shell", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>
  );

  expect(screen.getByRole("heading", { name: /easy-manim/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /登录/i })).toBeInTheDocument();
});

test("authenticated access to /threads/:threadId reaches the video thread page", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (
      path === "/api/video-threads/thread-target-001/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      // Keep the route in loading state so the test only verifies route reachability.
      return new Promise<Response>(() => {});
    }

    return new Response("not found", { status: 404 });
  };

  render(
    <MemoryRouter initialEntries={["/threads/thread-target-001"]}>
      <App />
    </MemoryRouter>
  );

  expect(await screen.findByText("Loading video thread…")).toBeInTheDocument();
});
