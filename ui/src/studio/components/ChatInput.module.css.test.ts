import chatInputStyles from "../styles/ChatInput.module.css?raw";

test("chat input keeps keyboard focus visible without relying on outline none", () => {
  expect(chatInputStyles).not.toMatch(/\.textarea\s*\{[\s\S]*outline:\s*none;/);
  expect(chatInputStyles).toMatch(
    /\.textarea:focus-visible\s*\{[\s\S]*outline-color:\s*var\(--color-pink-400\);/
  );
  expect(chatInputStyles).toMatch(
    /\.inputWrapper:focus-within\s*\{[\s\S]*border-color:\s*var\(--color-pink-300\);/
  );
});
