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

  expect(screen.getByText(/面向数学动画的智能创作平台/i)).toBeInTheDocument();
  expect(screen.getByText(/管理员命令行中执行 issue-token 命令获取/i)).toBeInTheDocument();
  await user.type(screen.getByLabelText(/智能体令牌/i), "easy-manim.agent-a.secret");
  await user.click(screen.getByRole("button", { name: /登录/i }));

  await waitFor(() => {
    expect(localStorage.getItem("easy_manim_session_token")).toBe("sess-token-1");
  });
  expect(fetchCalls.some((call) => call.url.toString().includes("/api/sessions"))).toBe(true);
});
