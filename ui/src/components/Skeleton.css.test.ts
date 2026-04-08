import skeletonStyles from "./Skeleton.css?raw";

test("skeleton surfaces use theme-aware color variables instead of hard-coded rgba", () => {
  expect(skeletonStyles).toMatch(/--skeleton-highlight-soft:/);
  expect(skeletonStyles).not.toMatch(/rgba\(/);
});
