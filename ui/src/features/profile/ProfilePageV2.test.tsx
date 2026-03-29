import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { ToastProvider } from "../../components/Toast";
import { ProfilePageV2 } from "./ProfilePageV2";

test("renders translated profile status", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/profile") {
      return new Response(
        JSON.stringify({
          agent_id: "agent-a",
          name: "Agent A",
          status: "active",
          profile_version: 2,
          profile_json: { style_hints: { text_language: "zh" } },
          policy_json: {},
          created_at: "2030-01-01T00:00:00Z",
          updated_at: "2030-01-01T00:00:00Z",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/profile/scorecard") {
      return new Response(
        JSON.stringify({
          completed_count: 8,
          failed_count: 1,
          failed_count_recent: 1,
          median_quality_score: 0.91,
          top_issue_codes: [{ code: "static_previews", count: 2 }],
          recent_profile_digests: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/runtime/status") {
      return new Response(
        JSON.stringify({
          provider: {
            mode: "stub",
            configured: true,
            api_base_present: false,
          },
          worker: {
            embedded: true,
            workers: [],
          },
          capabilities: {
            rollout_profile: "supervised",
            effective: {
              agent_learning_auto_apply_enabled: true,
              auto_repair_enabled: false,
              multi_agent_workflow_enabled: true,
              strategy_promotion_enabled: false,
            },
          },
          features: {
            mathtex: {
              checked: false,
              available: true,
              missing_checks: [],
              smoke_error: null,
            },
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/profile/suggestions") {
      return new Response(
        JSON.stringify({
          items: [
            {
              suggestion_id: "sugg-1",
              agent_id: "agent-a",
              patch: { style_hints: { tone: "teaching" } },
              rationale: {
                confidence: 0.92,
                supporting_evidence_counts: {
                  "style_hints.tone": 2,
                },
              },
              status: "pending",
              created_at: "2030-01-01T00:00:00Z",
              applied_at: null,
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
      <ToastProvider>
        <ProfilePageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByText(/agent a/i)).toBeInTheDocument();
  // 使用更灵活的文本匹配，因为 emoji 和文本可能在不同元素中
  expect(screen.getByText((content) => content.includes("启用中"))).toBeInTheDocument();
  expect(screen.getByText(/rollout: supervised/i)).toBeInTheDocument();
  expect(screen.getByText(/static_previews \(2\)/i)).toBeInTheDocument();
  expect(screen.getByText(/confidence 0.92/i)).toBeInTheDocument();
});
