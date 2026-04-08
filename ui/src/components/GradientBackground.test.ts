import gradientBackgroundSource from "./GradientBackground.tsx?raw";
import kawaiiDecorationsSource from "./KawaiiDecorations.tsx?raw";

test("active decorative components use design tokens instead of hard-coded hex palettes", () => {
  expect(gradientBackgroundSource).not.toMatch(/#(?:[0-9a-fA-F]{3}){1,2}/);
  expect(kawaiiDecorationsSource).not.toMatch(/#(?:[0-9a-fA-F]{3}){1,2}/);
  expect(gradientBackgroundSource).toMatch(/var\(--color-/);
  expect(kawaiiDecorationsSource).toMatch(/var\(--color-/);
});

test("reduced-motion branch builds a valid static background instead of nesting gradient strings", () => {
  expect(gradientBackgroundSource).not.toMatch(
    /radial-gradient\([^\n`]*\$\{colorSchemes\[scheme\]\[0\]\}/
  );
});
