import { test, expect } from "@playwright/test";

test("reviews profile suggestions and eval history (mock api)", async ({ page }) => {
  const suggestions: Array<any> = [
    {
      suggestion_id: "sug-1",
      agent_id: "agent-a",
      status: "pending",
      patch_json: { style_hints: { tone: "warm" } },
      rationale_json: { reason: "Based on recent runs." },
      provenance_json: {},
      created_at: "2030-01-01T00:00:00Z",
      applied_at: null
    }
  ];

  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_token: "sess-token-1",
        agent_id: "agent-a",
        name: "Agent A",
        expires_at: "2030-01-01T00:00:00Z"
      })
    });
  });

  await page.route("**/api/tasks", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });

  await page.route("**/api/profile", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        agent_id: "agent-a",
        name: "Agent A",
        status: "active",
        profile_version: 1,
        profile_json: { style_hints: { tone: "neutral" }, output_profile: { length: "short" }, validation_profile: {} },
        policy_json: {},
        created_at: "2030-01-01T00:00:00Z",
        updated_at: "2030-01-01T00:00:00Z"
      })
    });
  });

  await page.route("**/api/profile/scorecard", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        completed_count: 3,
        failed_count: 1,
        failed_count_recent: 1,
        median_quality_score: 0.8,
        top_issue_codes: ["bad_color"],
        recent_profile_digests: ["digest-a"]
      })
    });
  });

  await page.route("**/api/profile/apply", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ applied: true }) });
  });

  await page.route("**/api/profile/suggestions", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: suggestions }) });
  });

  await page.route("**/api/profile/suggestions/generate", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    suggestions.unshift({
      suggestion_id: "sug-2",
      agent_id: "agent-a",
      status: "pending",
      patch_json: { output_profile: { length: "short" } },
      rationale_json: {},
      provenance_json: {},
      created_at: "2030-01-01T00:00:00Z",
      applied_at: null
    });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: suggestions }) });
  });

  await page.route("**/api/profile/suggestions/sug-1/apply", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    suggestions[0] = { ...suggestions[0], status: "applied" };
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ applied: true, suggestion: suggestions[0] })
    });
  });

  await page.route("**/api/profile/suggestions/sug-1/dismiss", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    suggestions[0] = { ...suggestions[0], status: "dismissed" };
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ dismissed: true, suggestion: suggestions[0] })
    });
  });

  await page.route("**/api/profile/evals", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
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
      })
    });
  });

  await page.route("**/api/profile/evals/run-1", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "run-1",
        suite_id: "suite-a",
        provider: "mock",
        total_cases: 4,
        items: [],
        report: { success_rate: 0.75 }
      })
    });
  });

  await page.goto("/login");
  await page.getByLabel("Agent token").fill("easy-manim.agent-a.secret");
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page.getByRole("heading", { name: /^tasks$/i })).toBeVisible();

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: /^profile$/i })).toBeVisible();
  await expect(page.getByText("sug-1")).toBeVisible();

  await page.getByRole("button", { name: /generate suggestions/i }).click();
  await expect(page.getByText("sug-2")).toBeVisible();

  await page.goto("/evals");
  await expect(page.getByRole("heading", { name: /^evals$/i })).toBeVisible();
  await expect(page.getByText("run-1")).toBeVisible();
  await page.getByText("run-1").click();
  await expect(page.getByText(/suite-a/i)).toBeVisible();
});
