import loginPageStyles from "./LoginPage.css?raw";

test("login page allows vertical scrolling on short viewports", () => {
  expect(loginPageStyles).toMatch(/\.login-page\s*\{[\s\S]*overflow-y:\s*auto;/);
  expect(loginPageStyles).toMatch(/\.login-page\s*\{[\s\S]*overflow-x:\s*hidden;/);
});

test("login page stays constrained to the viewport while remaining scrollable", () => {
  expect(loginPageStyles).toMatch(/\.login-page\s*\{[\s\S]*height:\s*100dvh;/);
  expect(loginPageStyles).toMatch(/\.login-page\s*\{[\s\S]*overflow-y:\s*auto;/);
});

test("login page keeps legacy vh as a fallback instead of overriding modern viewport units", () => {
  expect(loginPageStyles).toMatch(
    /\.login-page\s*\{[\s\S]*min-height:\s*100vh;[\s\S]*min-height:\s*100svh;[\s\S]*height:\s*100dvh;/
  );
});

test("login form inputs preserve a visible keyboard focus ring", () => {
  expect(loginPageStyles).not.toMatch(/\.form-input\s*\{[\s\S]*outline:\s*none;/);
  expect(loginPageStyles).toMatch(
    /\.form-input:focus-visible\s*\{[\s\S]*outline-color:\s*var\(--color-pink-500\);/
  );
});

test("login page decorative surfaces rely on theme variables instead of hard-coded rgba or hex colors", () => {
  expect(loginPageStyles).toMatch(/--login-bg-orb-pink:/);
  expect(loginPageStyles).not.toMatch(/rgba\(/);
  expect(loginPageStyles).not.toMatch(/#[0-9a-fA-F]{3,8}/);
});
