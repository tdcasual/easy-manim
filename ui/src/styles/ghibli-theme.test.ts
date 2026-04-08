import ghibliThemeStyles from "./ghibli-theme.css?raw";

test("ghibli inputs keep a visible keyboard focus style", () => {
  expect(ghibliThemeStyles).not.toMatch(/\.input-ghibli\s*\{[\s\S]*outline:\s*none;/);
  expect(ghibliThemeStyles).toMatch(
    /\.input-ghibli:focus-visible\s*\{[\s\S]*outline-color:\s*var\(--focus\);/
  );
});
