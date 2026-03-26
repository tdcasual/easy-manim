import indexHtml from "../../index.html?raw";

test("index document defaults to Chinese locale metadata", () => {
  expect(indexHtml).toContain('<html lang="zh-CN">');
  expect(indexHtml).toContain("<title>easy-manim 控制台</title>");
});
