import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { App } from "./App";
import { clearSessionToken, writeSessionToken } from "../lib/session";

function mockViewport(isMobile: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => ({
      matches: query.includes("max-width: 1024px") ? isMobile : false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

test("mobile closed sidebar stays out of the accessibility tree until opened", async () => {
  const user = userEvent.setup();
  writeSessionToken("sess-token-1");
  mockViewport(true);

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <App />
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: /任务管理/i })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /退出登录/i })).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /打开菜单/i }));

  expect(screen.getByRole("button", { name: /退出登录/i })).toBeInTheDocument();

  clearSessionToken();
});
