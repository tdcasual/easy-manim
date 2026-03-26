import themeV2Styles from "./theme-v2.css?raw";

test("theme-v2 textarea utility shares input base styles without CSS Modules compose", () => {
  expect(themeV2Styles).not.toMatch(/\bcomposes\s*:/);
  expect(themeV2Styles).toMatch(/\.input,\s*\.textarea\s*\{/);
  expect(themeV2Styles).toMatch(/\.input::placeholder,\s*\.textarea::placeholder\s*\{/);
  expect(themeV2Styles).toMatch(/\.input:focus,\s*\.textarea:focus\s*\{/);
});
