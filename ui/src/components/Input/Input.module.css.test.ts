import inputStyles from "./Input.module.css?raw";

test("shared input controls keep small variants at least 44px tall", () => {
  expect(inputStyles).toMatch(/\.inputContainer\.sm\s*\{[^}]*min-height:\s*44px;/);
  expect(inputStyles).toMatch(/\.selectContainer\.sm\s*\{[^}]*min-height:\s*44px;/);
});

test("shared checkbox and radio controls keep a 44px hit area", () => {
  expect(inputStyles).toMatch(/\.checkbox\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
  expect(inputStyles).toMatch(/\.radio\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
});

test("shared inputs avoid hard-coded rgba focus styles and use a CSS chevron for select arrows", () => {
  expect(inputStyles).toMatch(/--input-focus-ring-pink:/);
  expect(inputStyles).toMatch(/\.selectContainer::after\s*\{/);
  expect(inputStyles).not.toMatch(/background-image:\s*url\(/);
  expect(inputStyles).not.toMatch(/rgba\(/);
});
