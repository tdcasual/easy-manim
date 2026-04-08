import buttonStyles from "./Button.module.css?raw";

test("shared buttons keep tap targets at least 44px", () => {
  expect(buttonStyles).toMatch(/\.button\.xs\s*\{[^}]*min-height:\s*44px;/);
  expect(buttonStyles).toMatch(/\.button\.sm\s*\{[^}]*min-height:\s*44px;/);
  expect(buttonStyles).toMatch(/\.iconButton\.xs\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
  expect(buttonStyles).toMatch(/\.iconButton\.sm\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
});

test("shared button shadows are defined with theme-aware variables instead of hard-coded rgba", () => {
  expect(buttonStyles).toMatch(/--button-shadow-pink-sm:/);
  expect(buttonStyles).toMatch(/--button-shadow-neutral-md:/);
  expect(buttonStyles).not.toMatch(/rgba\(/);
});
