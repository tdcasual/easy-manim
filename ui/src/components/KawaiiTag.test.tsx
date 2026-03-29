import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { writeLocale } from "../app/locale";
import { KawaiiTag } from "./KawaiiTag";

beforeEach(() => {
  writeLocale("zh-CN");
});

test("closable tags expose a locale-aware remove label", async () => {
  writeLocale("en-US");
  const user = userEvent.setup();
  const onClose = vi.fn();

  render(
    <KawaiiTag closable onClose={onClose}>
      Agent A
    </KawaiiTag>
  );

  await user.click(screen.getByRole("button", { name: /remove tag/i }));

  expect(onClose).toHaveBeenCalledTimes(1);
});
