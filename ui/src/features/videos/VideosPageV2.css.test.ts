import videosStyles from "./VideosPageV2.css?raw";

test("videos page scopes shared shell overrides to the videos page root", () => {
  expect(videosStyles).toMatch(/\.page-v2\.kawaii-page\s+\.page-eyebrow\s*\{/);
  expect(videosStyles).toMatch(/\.page-v2\.kawaii-page\s+\.refresh-btn\s*\{/);
  expect(videosStyles).toMatch(/\.page-v2\.kawaii-page\s+\.empty-state-v2\s*\{/);
  expect(videosStyles).not.toMatch(/^\s*\.page-eyebrow\s*\{/m);
  expect(videosStyles).not.toMatch(/^\s*\.refresh-btn\s*\{/m);
  expect(videosStyles).not.toMatch(/^\s*\.empty-state-v2\s*\{/m);
});
