import taskDetailStyles from "./TaskDetailPageV2.css?raw";

test("task review feedback dismiss control keeps a 44px target and focus ring", () => {
  expect(taskDetailStyles).toMatch(
    /\.task-review-panel__feedback-dismiss\s*\{[\s\S]*width:\s*44px;/
  );
  expect(taskDetailStyles).toMatch(
    /\.task-review-panel__feedback-dismiss\s*\{[\s\S]*height:\s*44px;/
  );
  expect(taskDetailStyles).toMatch(
    /\.task-review-panel__feedback-dismiss:focus-visible\s*\{[\s\S]*outline-color:\s*var\(--focus\);/
  );
});

test("task detail panels define semantic surface variables instead of raw rgba colors", () => {
  expect(taskDetailStyles).toMatch(/--task-surface-soft:/);
  expect(taskDetailStyles).toMatch(/--task-border-info:/);
});
