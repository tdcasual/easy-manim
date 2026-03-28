import appStyles from "./App.css?raw";

test("collapsed desktop sidebar keeps the toggle available", () => {
  expect(appStyles).not.toMatch(
    /\.sidebar\.collapsed\s+\.sidebar-toggle\s*\{[^}]*display:\s*none;/
  );
});
