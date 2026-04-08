import errorBoundaryStyles from "./ErrorBoundary.css?raw";

test("error boundary surfaces use semantic color mixing instead of hard-coded rgba", () => {
  expect(errorBoundaryStyles).toMatch(/--error-boundary-surface:/);
  expect(errorBoundaryStyles).not.toMatch(/rgba\(/);
});
