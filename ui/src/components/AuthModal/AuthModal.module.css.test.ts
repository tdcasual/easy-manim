import authModalStyles from "./AuthModal.module.css?raw";

test("auth modal disables collapsed trigger motion for reduced-motion users", () => {
  expect(authModalStyles).toMatch(
    /\.collapsed\s*\{[\s\S]*animation:\s*pulse 2s ease-in-out infinite;/
  );
  expect(authModalStyles).toMatch(
    /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*\.collapsed[\s\S]*animation:\s*none;/
  );
});
