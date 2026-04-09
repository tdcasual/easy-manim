import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { writeLocale } from "../../app/locale";
import { VideoStage } from "./VideoStage";

beforeEach(() => {
  writeLocale("en-US");
});

test("compact layout marks stage as compact while keeping empty-state guidance", () => {
  render(<VideoStage compact />);

  const stage = screen.getByRole("region", { name: /video stage/i });
  expect(stage).toHaveAttribute("data-stage-layout", "compact");
  expect(screen.getByText(/start your creative journey/i)).toBeInTheDocument();
});

test("default layout keeps the standard stage density", () => {
  render(<VideoStage />);

  const stage = screen.getByRole("region", { name: /video stage/i });
  expect(stage).toHaveAttribute("data-stage-layout", "default");
});
