import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { writeLocale } from "../app/locale";
import { SkipLink } from "./SkipLink";

beforeEach(() => {
  writeLocale("zh-CN");
});

test("renders a visually hidden skip link that targets main content", () => {
  render(<SkipLink />);

  const link = screen.getByRole("link", { name: /跳转到主内容/i });
  expect(link).toBeInTheDocument();
  expect(link).toHaveAttribute("href", "#main-content");
  expect(link).toHaveClass("sr-only");
});

test("shows english label when locale is en-US", () => {
  writeLocale("en-US");
  render(<SkipLink />);

  const link = screen.getByRole("link", { name: /Skip to main content/i });
  expect(link).toBeInTheDocument();
});
