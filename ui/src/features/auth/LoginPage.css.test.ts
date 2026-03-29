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
    /\.login-page\s*\{[\s\S]*min-height:\s*100vh;[\s\S]*min-height:\s*100svh;[\s\S]*height:\s*100dvh;/,
  );
});
