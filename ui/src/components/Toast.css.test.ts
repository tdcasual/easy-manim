import toastStyles from "./Toast.css?raw";

test("toast close button keeps a 44px touch target with visible keyboard focus", () => {
  expect(toastStyles).toMatch(/\.toast-close\s*\{[\s\S]*width:\s*44px;/);
  expect(toastStyles).toMatch(/\.toast-close\s*\{[\s\S]*height:\s*44px;/);
  expect(toastStyles).toMatch(
    /\.toast-close:focus-visible\s*\{[\s\S]*outline-color:\s*var\(--focus\);/
  );
  expect(toastStyles).not.toMatch(/rgba\(/);
});
