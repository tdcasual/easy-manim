import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { EvalDetailPageV2 } from "./EvalDetailPageV2";

test("renders translated eval case statuses", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile/evals/run-1") {
      return new Response(
        JSON.stringify({
          run_id: "run-1",
          suite_id: "suite-smoke",
          provider: "mock",
          total_cases: 1,
          report: { success_rate: 1 },
          items: [
            {
              task_id: "task-1",
              root_task_id: "task-1",
              status: "completed",
              duration_seconds: 1.25,
              issue_codes: [],
              manual_review_required: false
            }
          ]
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/evals/run-1"]}>
      <Routes>
        <Route path="/evals/:runId" element={<EvalDetailPageV2 />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "评测详情" })).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
});
