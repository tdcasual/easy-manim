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
          report: { success_rate: 0, delivery_rate: 1 },
          items: [
            {
              task_id: "task-1",
              root_task_id: "task-1",
              status: "completed",
              delivery_passed: true,
              quality_passed: false,
              duration_seconds: 1.25,
              issue_codes: [],
              manual_review_required: false,
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/profile/strategy-decisions") {
      return new Response(
        JSON.stringify({
          items: [
            {
              kind: "strategy_promotion_shadow",
              recorded_at: "2030-01-01T00:00:00Z",
              strategy_id: "strategy-1",
              challenger_run_id: "run-1",
              promotion_recommended: false,
              promotion_decision: {
                mode: "shadow",
                approved: false,
                reasons: ["quality_gain_too_small"],
                deltas: { accepted_quality_rate: 0.002 },
              },
            },
          ],
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
  expect(screen.getByText("质量通过率")).toBeInTheDocument();
  expect(screen.getByText("交付率")).toBeInTheDocument();
  expect(screen.getByText("仅完成交付")).toBeInTheDocument();
  expect(screen.getByText("strategy-1")).toBeInTheDocument();
  expect(screen.getByText(/quality_gain_too_small/i)).toBeInTheDocument();
  expect(screen.getByText(/^shadow$/i)).toBeInTheDocument();
});
