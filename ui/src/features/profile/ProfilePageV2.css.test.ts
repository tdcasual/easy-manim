import profileStyles from "./ProfilePageV2.css?raw";

test("profile page scopes shared shell overrides to the kawaii page root", () => {
  expect(profileStyles).toMatch(/\.page-kawaii\s+\.page-header-v2\s*\{/);
  expect(profileStyles).toMatch(/\.page-kawaii\s+\.page-eyebrow\s*\{/);
  expect(profileStyles).toMatch(/\.page-kawaii\s+\.metrics-grid-v2\s*\{/);
  expect(profileStyles).not.toMatch(/^\s*\.page-header-v2\s*\{/m);
  expect(profileStyles).not.toMatch(/^\s*\.page-eyebrow\s*\{/m);
  expect(profileStyles).not.toMatch(/^\s*\.metrics-grid-v2\s*\{/m);
});

test("profile page keeps custom checkbox hit areas at least 44px", () => {
  expect(profileStyles).toMatch(/\.checkbox-wrapper\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
  expect(profileStyles).toMatch(
    /\.checkbox-wrapper input\[type="checkbox"\]:focus-visible \+ \.checkbox-custom\s*\{/
  );
});

test("profile page styles rely on tokens instead of hard-coded rgba or hex fallbacks", () => {
  expect(profileStyles).toMatch(/--profile-text-shadow-soft:/);
  expect(profileStyles).not.toMatch(/rgba\(/);
  expect(profileStyles).not.toMatch(/#[0-9a-fA-F]{3,8}/);
});
