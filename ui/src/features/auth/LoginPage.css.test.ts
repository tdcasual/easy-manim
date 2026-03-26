import loginPageStyles from "./LoginPage.css?raw";

test("login page allows vertical scrolling on short viewports", () => {
  expect(loginPageStyles).toMatch(/\.login-page\s*\{[\s\S]*overflow-y:\s*auto;/);
  expect(loginPageStyles).toMatch(/\.login-page\s*\{[\s\S]*overflow-x:\s*hidden;/);
});
