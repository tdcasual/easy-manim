import kawaiiTagStyles from "./KawaiiTag.css?raw";

test("closable tags expand the remove affordance to a touch-friendly hit area", () => {
  expect(kawaiiTagStyles).toMatch(
    /\.kawaii-tag\.closable \.tag-close::before\s*\{[\s\S]*inset:\s*-13px;/
  );
  expect(kawaiiTagStyles).toMatch(
    /\.kawaii-tag\.closable \.tag-close:focus-visible\s*\{[\s\S]*outline-color:\s*currentColor;/
  );
});

test("kawaii tag surfaces and badge accents avoid hard-coded rgba or hex values", () => {
  expect(kawaiiTagStyles).toMatch(/--kawaii-tag-badge-surface:/);
  expect(kawaiiTagStyles).not.toMatch(/rgba\(/);
  expect(kawaiiTagStyles).not.toMatch(/#[0-9a-fA-F]{3,8}/);
});
