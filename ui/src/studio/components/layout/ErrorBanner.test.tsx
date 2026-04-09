import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { writeLocale } from "../../../app/locale";
import { ErrorBanner } from "./ErrorBanner";

beforeEach(() => {
  writeLocale("zh-CN");
});

test("error banner follows the active locale", async () => {
  writeLocale("en-US");
  const user = userEvent.setup();
  const onRetry = vi.fn();
  const onClose = vi.fn();

  render(
    <ErrorBanner
      error={{ type: "network", message: "Connection lost", retryable: true }}
      onRetry={onRetry}
      onClose={onClose}
    />
  );

  expect(screen.getByRole("alert")).toHaveTextContent(/Network connection failed/i);

  await user.click(screen.getByRole("button", { name: /retry/i }));
  await user.click(screen.getByRole("button", { name: /close error banner/i }));

  expect(onRetry).toHaveBeenCalledTimes(1);
  expect(onClose).toHaveBeenCalledTimes(1);
});
