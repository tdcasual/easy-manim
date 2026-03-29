import tasksPageStyles from "./TasksPageV2.css?raw";

test("tasks page keeps stat cards readable on mobile", () => {
  expect(tasksPageStyles).toMatch(
    /@media \(max-width:\s*640px\)\s*\{[\s\S]*\.kawaii-stats\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);/
  );
  expect(tasksPageStyles).toMatch(/\.stat-label\s*\{[\s\S]*white-space:\s*nowrap;/);
});
