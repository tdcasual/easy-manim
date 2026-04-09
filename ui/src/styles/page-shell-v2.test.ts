import pageShellStyles from "./page-shell-v2.css?raw";

test("shared V2 page shell defines the common layout classes reused across routes", () => {
  expect(pageShellStyles).toMatch(/\.page-v2\s*\{/);
  expect(pageShellStyles).toMatch(/\.section-card-v2\s*\{/);
  expect(pageShellStyles).toMatch(/\.content-grid-v2\s*\{/);
  expect(pageShellStyles).toMatch(/\.refresh-btn\s*\{/);
});
