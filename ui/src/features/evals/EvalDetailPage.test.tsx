import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { EvalDetailPage } from "./EvalDetailPage";

test("shows eval run details and case list", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile/evals/run-1") {
      return new Response(
        JSON.stringify({
          run_id: "run-1",
          suite_id: "suite-a",
          provider: "mock",
          total_cases: 2,
          items: [
            {
              task_id: "task-1",
              root_task_id: "task-1",
              status: "failed",
              duration_seconds: 1.2,
              issue_codes: ["bad_color"],
              quality_score: 0.2,
              manual_review_required: true
            },
            {
              task_id: "task-2",
              root_task_id: "task-2",
              status: "completed",
              duration_seconds: 0.8,
              issue_codes: [],
              quality_score: 0.9
            }
          ],
          report: { success_rate: 0.5 }
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/evals/run-1"]}>
      <Routes>
        <Route path="/evals/:runId" element={<EvalDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(screen.getByText(/正在加载/i)).toBeInTheDocument();
  expect(await screen.findByText(/suite-a/i)).toBeInTheDocument();
  expect(screen.getByText("task-1")).toBeInTheDocument();
  expect(screen.getByText(/bad_color/i)).toBeInTheDocument();
  expect(screen.getByText("task-2")).toBeInTheDocument();
});
