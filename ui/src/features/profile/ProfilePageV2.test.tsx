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
          completed_count: 999,
          quality_passed_count: 8,
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
              multi_agent_workflow_auto_challenger_enabled: true,
              multi_agent_workflow_auto_arbitration_enabled: false,
              multi_agent_workflow_guarded_rollout_enabled: false,
              strategy_promotion_enabled: false,
            },
          },
          autonomy_guard: {
            enabled: true,
            allowed: false,
            reasons: ["branch_rejection_rate_above_threshold"],
            canary_available: true,
            canary_delivered: true,
            delivery_rate: 1,
            min_delivery_rate: 0.9,
            emergency_fallback_rate: 0,
            max_emergency_fallback_rate: 0.1,
            branch_rejection_rate: 1,
            max_branch_rejection_rate: 0.25,
          },
          delivery_summary: {
            total_roots: 8,
            delivered_roots: 7,
            failed_roots: 1,
            pending_roots: 0,
            delivery_rate: 0.875,
            emergency_fallback_rate: 0.125,
            case_status_counts: {
              completed: 5,
              branching: 2,
              arbitrating: 1,
            },
            agent_run_status_counts: {
              completed: 6,
              failed: 1,
              queued: 2,
              running: 1,
            },
            agent_run_role_status_counts: {
              generator: {
                completed: 4,
                failed: 1,
                queued: 2,
              },
              planner: {
                completed: 5,
              },
              reviewer: {
                completed: 5,
                running: 1,
              },
            },
            agent_run_stop_reason_counts: {
              provider_timeout: 1,
              render_failed: 2,
            },
            completion_modes: {
              primary: 4,
              repaired: 2,
              emergency_fallback: 1,
            },
            challenger_branches_completed: 2,
            challenger_branches_rejected: 1,
            branch_rejection_rate: 0.5,
            arbitration_attempts: 2,
            arbitration_successes: 1,
            arbitration_success_rate: 0.5,
            repair_loop_saturation_count: 0,
            repair_loop_saturation_rate: 0,
            top_stop_reasons: [],
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
    if (path === "/api/profile/strategies") {
      return new Response(
        JSON.stringify({
          items: [
            {
              strategy_id: "strategy-geometry",
              scope: "global",
              prompt_cluster: "geometry",
              status: "active",
              routing_keywords: ["triangle", "geometry"],
              params: {
                routing: { keywords: ["triangle", "geometry"] },
                style_hints: { tone: "teaching" },
              },
              guarded_rollout: {
                consecutive_shadow_passes: 2,
                rollback_armed: true,
              },
              last_eval_run: {
                promotion_mode: "guarded_auto_apply",
              },
              created_at: "2030-01-01T00:00:00Z",
              updated_at: "2030-01-01T00:00:00Z",
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
  expect(screen.getByText("质量通过")).toBeInTheDocument();
  expect(screen.queryByText("999")).not.toBeInTheDocument();
  expect(screen.getByText(/rollout: supervised/i)).toBeInTheDocument();
  expect(screen.getByText(/static_previews \(2\)/i)).toBeInTheDocument();
  expect(screen.getByText(/confidence 0.92/i)).toBeInTheDocument();
  expect(screen.getByText(/strategy routing/i)).toBeInTheDocument();
  expect(screen.getByText(/strategy-geometry/i)).toBeInTheDocument();
  expect(screen.getByText(/triangle, geometry/i)).toBeInTheDocument();
  expect(screen.getByText(/shadow passes: 2/i)).toBeInTheDocument();
  expect(screen.getByText(/auto challenger: enabled/i)).toBeInTheDocument();
  expect(screen.getByText(/auto arbitration: disabled/i)).toBeInTheDocument();
  expect(screen.getByText(/guarded rollout: disabled/i)).toBeInTheDocument();
  expect(screen.getByText(/guarded autonomy: blocked/i)).toBeInTheDocument();
  expect(screen.getByText(/branch_rejection_rate_above_threshold/i)).toBeInTheDocument();
  expect(
    screen.getByText(/cases: arbitrating 1 \| branching 2 \| completed 5/i)
  ).toBeInTheDocument();
  expect(
    screen.getByText(/agent runs: completed 6 \| failed 1 \| queued 2 \| running 1/i)
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /agent roles: generator \[completed 4 \| failed 1 \| queued 2\] \| planner \[completed 5\] \| reviewer \[completed 5 \| running 1\]/i
    )
  ).toBeInTheDocument();
  expect(
    screen.getByText(/agent stop reasons: provider_timeout 1 \| render_failed 2/i)
  ).toBeInTheDocument();
  expect(
    screen.getByText(/completion modes: emergency_fallback 1 \| primary 4 \| repaired 2/i)
  ).toBeInTheDocument();
});
