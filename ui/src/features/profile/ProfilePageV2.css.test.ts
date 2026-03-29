import profileStyles from "./ProfilePageV2.css?raw";

test("profile page scopes shared shell overrides to the kawaii page root", () => {
  expect(profileStyles).toMatch(/\.page-kawaii\s+\.page-header-v2\s*\{/);
  expect(profileStyles).toMatch(/\.page-kawaii\s+\.page-eyebrow\s*\{/);
  expect(profileStyles).toMatch(/\.page-kawaii\s+\.metrics-grid-v2\s*\{/);
  expect(profileStyles).not.toMatch(/^\s*\.page-header-v2\s*\{/m);
  expect(profileStyles).not.toMatch(/^\s*\.page-eyebrow\s*\{/m);
  expect(profileStyles).not.toMatch(/^\s*\.metrics-grid-v2\s*\{/m);
});
