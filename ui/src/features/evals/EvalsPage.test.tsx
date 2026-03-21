import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { EvalsPage } from "./EvalsPage";
import { EvalDetailPage } from "./EvalDetailPage";

test("lists eval runs and opens a run detail view", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile/evals" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              run_id: "run-1",
              suite_id: "suite-a",
              provider: "mock",
              total_cases: 4,
              items: [],
              report: { success_rate: 0.75 }
            }
          ]
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/profile/evals/run-1" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          run_id: "run-1",
          suite_id: "suite-a",
          provider: "mock",
          total_cases: 4,
          items: [],
          report: { success_rate: 0.75 }
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/evals"]}>
      <Routes>
        <Route path="/evals" element={<EvalsPage />} />
        <Route path="/evals/:runId" element={<EvalDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByText("run-1")).toBeInTheDocument();
});

