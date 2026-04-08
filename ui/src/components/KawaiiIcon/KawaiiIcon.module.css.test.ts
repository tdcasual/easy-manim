import kawaiiIconStyles from "./KawaiiIcon.module.css?raw";

test("interactive kawaii icon buttons keep tap targets at least 44px", () => {
  expect(kawaiiIconStyles).toMatch(/\.iconButton\.xs\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
  expect(kawaiiIconStyles).toMatch(/\.iconButton\.sm\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;/);
});

test("kawaii icon shadows are token-driven instead of hard-coded rgba", () => {
  expect(kawaiiIconStyles).toMatch(/--kawaii-icon-shadow-pink:/);
  expect(kawaiiIconStyles).not.toMatch(/rgba\(/);
});
