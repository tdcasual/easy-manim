import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { EvalsPageV2 } from "./EvalsPageV2";

test("shows an error state instead of an empty state when eval loading fails", async () => {
  writeSessionToken("sess-token-1");

  globalThis.fetch = vi.fn(async () => new Response("boom", { status: 500 }));

  render(
    <MemoryRouter>
      <EvalsPageV2 />
    </MemoryRouter>
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(/加载评测记录失败/i);
  expect(screen.queryByText(/还没有评测运行/i)).not.toBeInTheDocument();
});

test("renders recent shadow strategy decisions", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile/evals") {
      return new Response(
        JSON.stringify({
          items: [
            {
              run_id: "run-1",
              suite_id: "suite-a",
              provider: "mock",
              total_cases: 1,
              report: { success_rate: 0.75, delivery_rate: 1 },
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
    <MemoryRouter>
      <EvalsPageV2 />
    </MemoryRouter>
  );

  expect(await screen.findByText("strategy-1")).toBeInTheDocument();
  expect(screen.getByText("平均质量通过率")).toBeInTheDocument();
  expect(screen.getByText("平均交付率")).toBeInTheDocument();
  expect(screen.getByText(/交付 100%/i)).toBeInTheDocument();
  expect(screen.getByText(/quality_gain_too_small/i)).toBeInTheDocument();
  expect(screen.getByText(/strategy_promotion_shadow\s*·\s*shadow/i)).toBeInTheDocument();
});
