import workbenchStyles from "./VideoThreadWorkbench.css?raw";

test("video thread workbench relies on theme tokens instead of hard-coded overlay colors", () => {
  expect(workbenchStyles).toMatch(/--vtw-accent-border:/);
  expect(workbenchStyles).toMatch(/background:\s*var\(--vtw-panel-bg-strong\);/);
  expect(workbenchStyles).not.toMatch(/rgba\(/);
  expect(workbenchStyles).not.toContain("#08111c");
});
